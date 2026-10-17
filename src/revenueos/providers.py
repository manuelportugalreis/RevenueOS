"""Provider boundary: offline fixtures are explicitly distinct from live API execution."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderReply:
    content: str | None
    input_tokens: int | None
    output_tokens: int | None
    model: str
    response_id: str | None = None
    refusal: bool = False


class ProviderFailure(RuntimeError):
    def __init__(self, code: str, *, retriable: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.retriable = retriable


class Provider(Protocol):
    kind: str
    model: str

    def generate(self, payload: dict[str, Any], timeout_seconds: float) -> ProviderReply: ...


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise ProviderFailure("provider_redirect_denied")


def responses_transport(
    payload: dict[str, Any], key: str, timeout_seconds: float
) -> dict[str, Any]:
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=timeout_seconds
        ) as response:
            raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ProviderFailure("provider_response_too_large")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ProviderFailure("provider_invalid_envelope")
        return result
    except urllib.error.HTTPError as exc:
        # Provider bodies and authorization headers must never enter routine errors/logs.
        raise ProviderFailure(
            f"provider_http_{exc.code}", retriable=exc.code in (429, 500, 502, 503, 504)
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProviderFailure("provider_transport_failure", retriable=True) from None
    except (ValueError, UnicodeDecodeError):
        raise ProviderFailure("provider_invalid_envelope") from None


@dataclass
class OpenAIResponses:
    """Opt-in adapter. No implicit model, credentials, retries, pricing, or endpoint override."""

    model: str
    api_key: str = field(repr=False)
    enabled: bool = False
    transport: Callable[[dict[str, Any], str, float], dict[str, Any]] = field(
        default=responses_transport,
        repr=False,
    )
    kind: str = field(default="openai_live", init=False)

    @classmethod
    def from_environment(cls) -> OpenAIResponses:
        return cls(
            model=os.environ["REVENUEOS_MODEL"],
            api_key=os.environ["OPENAI_API_KEY"],
            enabled=os.environ.get("REVENUEOS_LIVE_ENABLED") == "1",
        )

    def generate(self, payload: dict[str, Any], timeout_seconds: float) -> ProviderReply:
        if not self.enabled or not self.api_key or not self.model:
            raise ProviderFailure("live_provider_disabled_or_unconfigured")
        request = {**payload, "model": self.model, "store": False, "tools": []}
        raw = self.transport(request, self.api_key, timeout_seconds)
        try:
            usage = raw.get("usage") or {}
            inputs, outputs = usage.get("input_tokens"), usage.get("output_tokens")
            if not all(
                value is None or (type(value) is int and value >= 0) for value in (inputs, outputs)
            ):
                raise ValueError("invalid usage")
            content = []
            refusal = False
            for item in raw.get("output", []):
                if item.get("type") != "message":
                    continue
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        content.append(part["text"])
                    elif part.get("type") == "refusal":
                        refusal = True
            # Non-completed envelopes cannot be treated as valid structured results.
            if raw.get("status") != "completed":
                content = []
            return ProviderReply(
                "".join(content) or None,
                inputs,
                outputs,
                str(raw.get("model", self.model)),
                raw.get("id"),
                refusal,
            )
        except (TypeError, KeyError, ValueError, AttributeError):
            raise ProviderFailure("provider_invalid_envelope") from None


@dataclass
class ScriptedProvider:
    """A test double, never a model-quality comparator. Token values are simulated."""

    script: Callable[[dict[str, Any], int], ProviderReply]
    model: str = "scripted-fixture-v1"
    kind: str = field(default="scripted_fixture", init=False)
    calls: int = field(default=0, init=False)

    def generate(self, payload: dict[str, Any], timeout_seconds: float) -> ProviderReply:
        self.calls += 1
        return self.script(payload, self.calls)
