"""Explicit free-tier-only Gemini experiment adapter; never used by the public demo."""

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from revenueos.providers import NoRedirect, ProviderFailure, ProviderReply

MODEL = "gemini-3.5-flash-lite"


def gemini_transport(payload: dict[str, Any], key: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
            raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ProviderFailure("provider_response_too_large")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("envelope")
        return value
    except urllib.error.HTTPError as exc:
        # No retries: preserve quota/errors and never log the key or response body.
        raise ProviderFailure(f"provider_http_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProviderFailure("provider_transport_failure") from None
    except (ValueError, UnicodeDecodeError):
        raise ProviderFailure("provider_invalid_envelope") from None


@dataclass
class FreeGemini:
    api_key: str = field(repr=False)
    free_tier_confirmed: bool = False
    max_calls: int = 24
    interval_seconds: float = 15
    transport: Callable[[dict[str, Any], str, float], dict[str, Any]] = field(
        default=gemini_transport, repr=False
    )
    model: str = field(default=MODEL, init=False)
    kind: str = field(default="gemini_free_live", init=False)
    calls: int = field(default=0, init=False)
    last_call: float = field(default=0, init=False)
    halt_reason: str | None = field(default=None, init=False)
    completed_generations: int = field(default=0, init=False)

    @classmethod
    def from_environment(cls, max_calls: int = 24) -> "FreeGemini":
        return cls(
            os.environ.get("GEMINI_API_KEY", ""),
            os.environ.get("REVENUEOS_FREE_TIER_CONFIRMED") == "1",
            max_calls=max_calls,
        )

    def generate(self, payload: dict[str, Any], timeout_seconds: float) -> ProviderReply:
        if not self.api_key or not self.free_tier_confirmed:
            raise ProviderFailure("free_tier_credentials_and_no_billing_attestation_required")
        if self.halt_reason:
            raise ProviderFailure("experiment_halted")
        if not 1 <= self.max_calls <= 48 or self.calls >= self.max_calls:
            raise ProviderFailure("experiment_call_limit")
        delay = max(0, self.last_call + self.interval_seconds - time.monotonic())
        # Pacing belongs in the experiment, before recommend() starts its deadline.
        if delay > 0.01:
            raise ProviderFailure("experiment_pacing_required")
        self.calls += 1
        self.last_call = time.monotonic()
        request = {
            "systemInstruction": {"parts": [{"text": payload["instructions"]}]},
            "contents": [{"role": "user", "parts": [{"text": payload["input"]}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": payload["text"]["format"]["schema"],
                "maxOutputTokens": payload["max_output_tokens"],
                "temperature": 0,
                "thinkingConfig": {"thinkingLevel": "minimal"},
            },
        }
        try:
            raw = self.transport(request, self.api_key, timeout_seconds)
        except ProviderFailure as exc:
            self.halt_reason = exc.code
            raise
        try:
            usage = raw.get("usageMetadata") or {}
            inputs = usage.get("promptTokenCount")
            outputs = usage.get("candidatesTokenCount")
            thoughts = usage.get("thoughtsTokenCount", 0)
            if not all(
                value is None or (type(value) is int and value >= 0)
                for value in (inputs, outputs, thoughts)
            ):
                raise ValueError("usage")
            candidates = raw.get("candidates") or []
            candidate = candidates[0] if candidates else {}
            stopped = candidate.get("finishReason") == "STOP"
            content = "".join(
                part.get("text", "")
                for part in candidate.get("content", {}).get("parts", [])
                if not part.get("thought")
            )
            if stopped and content:
                self.completed_generations += 1
            return ProviderReply(
                content if stopped and content else None,
                inputs,
                outputs + thoughts if outputs is not None and thoughts is not None else None,
                str(raw.get("modelVersion", self.model)),
                raw.get("responseId"),
                candidate.get("finishReason") in ("SAFETY", "RECITATION", "BLOCKLIST"),
            )
        except (TypeError, ValueError, AttributeError):
            raise ProviderFailure("provider_invalid_envelope") from None
