import pytest

from revenueos.providers import OpenAIResponses, ProviderFailure


def test_disabled_live_adapter_cannot_use_transport() -> None:
    calls = []
    provider = OpenAIResponses(
        "explicit-model", "fake-not-a-key", transport=lambda *args: calls.append(args)
    )
    with pytest.raises(ProviderFailure, match="disabled"):
        provider.generate({}, 1)
    assert calls == []


def test_responses_contract_without_network() -> None:
    seen = []

    def transport(payload: dict, key: str, timeout: float) -> dict:
        seen.append(payload)
        assert key == "fake-not-a-key" and timeout == 2
        return {
            "status": "completed",
            "id": "fixture-response",
            "model": "explicit-model",
            "usage": {"input_tokens": 15, "output_tokens": 7},
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"fixture":true}'}],
                }
            ],
        }

    provider = OpenAIResponses(
        "explicit-model", "fake-not-a-key", enabled=True, transport=transport
    )
    reply = provider.generate(
        {"input": "synthetic", "text": {"format": {"type": "json_schema"}}}, 2
    )
    assert reply.content == '{"fixture":true}' and reply.input_tokens == 15
    assert seen[0]["store"] is False and seen[0]["tools"] == []
    assert "fake-not-a-key" not in repr(provider)


@pytest.mark.parametrize(
    "status,parts,refusal",
    [
        ("incomplete", [{"type": "output_text", "text": "partial"}], False),
        ("completed", [{"type": "refusal", "refusal": "fixture refusal"}], True),
    ],
)
def test_incomplete_and_refusal_are_not_success(status: str, parts: list, refusal: bool) -> None:
    provider = OpenAIResponses(
        "explicit-model",
        "fake",
        enabled=True,
        transport=lambda *args: {
            "status": status,
            "output": [{"type": "message", "content": parts}],
        },
    )
    reply = provider.generate({}, 1)
    assert reply.content is None and reply.refusal == refusal
