import json

import pytest

from revenueos.free_provider import MODEL, FreeGemini
from revenueos.providers import ProviderFailure


def envelope(**changes: object) -> dict:
    return {
        "modelVersion": MODEL,
        "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 20},
        "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}],
        **changes,
    }


def payload() -> dict:
    return {
        "instructions": "synthetic only",
        "input": json.dumps({"query": "onboarding kickoff", "evidence": []}),
        "text": {"format": {"schema": {"type": "object"}}},
        "max_output_tokens": 1500,
    }


def test_free_adapter_requires_key_and_no_billing_attestation() -> None:
    calls = []
    provider = FreeGemini("fixture", transport=lambda *args: calls.append(args))
    with pytest.raises(ProviderFailure, match="attestation"):
        provider.generate(payload(), 2)
    assert not calls
    assert "fixture" not in repr(provider)


def test_free_adapter_schema_query_usage_and_call_cap() -> None:
    seen = []

    def transport(request: dict, key: str, timeout: float) -> dict:
        seen.append(request)
        return envelope()

    provider = FreeGemini("fake-key", True, max_calls=1, interval_seconds=0, transport=transport)
    result = provider.generate(payload(), 2)
    assert result.content == "{}" and result.input_tokens == 50 and result.output_tokens == 20
    assert provider.completed_generations == 1
    assert "onboarding kickoff" in seen[0]["contents"][0]["parts"][0]["text"]
    assert seen[0]["generationConfig"]["responseJsonSchema"] == {"type": "object"}
    assert "tools" not in seen[0]
    with pytest.raises(ProviderFailure, match="call_limit"):
        provider.generate(payload(), 2)
    assert len(seen) == 1


@pytest.mark.parametrize("count", [-1, True, "100"])
def test_invalid_usage_never_becomes_known_cost(count: object) -> None:
    provider = FreeGemini(
        "fixture",
        True,
        interval_seconds=0,
        transport=lambda *args: envelope(usageMetadata={"promptTokenCount": count}),
    )
    with pytest.raises(ProviderFailure, match="invalid_envelope"):
        provider.generate(payload(), 2)


def test_non_stop_completion_is_not_a_valid_recommendation() -> None:
    provider = FreeGemini(
        "fixture",
        True,
        transport=lambda *args: envelope(candidates=[{"finishReason": "MAX_TOKENS"}]),
    )
    assert provider.generate(payload(), 2).content is None
    assert provider.completed_generations == 0


def test_quota_failure_halts_experiment_without_retry_or_fallback() -> None:
    calls = []

    def transport(*args):
        calls.append(1)
        raise ProviderFailure("provider_http_429")

    provider = FreeGemini("fixture", True, interval_seconds=0, transport=transport)
    with pytest.raises(ProviderFailure, match="429"):
        provider.generate(payload(), 2)
    with pytest.raises(ProviderFailure, match="halted"):
        provider.generate(payload(), 2)
    assert len(calls) == 1 and provider.calls == 1
