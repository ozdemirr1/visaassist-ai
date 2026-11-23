"""Field extraction with a model (ADR 0007): schema, validation, the OpenAI client, the cost.

No test calls a provider: the model is a fake, and the OpenAI client talks to a mock transport.
"""

import json

import httpx
import pytest

from app.ai.client import ModelError, ModelReply, OpenAIClient
from app.ai.extraction import FieldSpec, extract, schema_for
from app.ai.prices import cost_usd

FIELDS = [
    FieldSpec("guest_name", "text", "Guest name"),
    FieldSpec("check_in", "date", "Check-in"),
    FieldSpec("nights", "int", "Nights"),
    FieldSpec("paid", "bool", "Paid"),
    FieldSpec("amount", "money", "Amount"),
]


class FakeModel:
    model = "gpt-6.1-terra"

    def __init__(self, data: dict) -> None:
        self.data = data
        self.calls: list[dict] = []

    def read(self, **kwargs) -> ModelReply:
        self.calls.append(kwargs)
        return ModelReply(self.data, self.model, 2500, 300, 1.5)


def test_the_schema_is_strict_and_every_value_may_be_null() -> None:
    schema = schema_for(FIELDS)
    assert schema["additionalProperties"] is False
    assert schema["required"] == [f.id for f in FIELDS]
    for f in FIELDS:
        item = schema["properties"][f.id]
        assert item["required"] == ["value", "confidence"] and item["additionalProperties"] is False
    assert schema["properties"]["check_in"]["properties"]["value"]["type"] == ["string", "null"]
    assert schema["properties"]["nights"]["properties"]["value"]["type"] == ["integer", "null"]
    money = schema["properties"]["amount"]["properties"]["value"]["anyOf"]
    assert {"type": "null"} in money


def test_values_are_checked_like_typed_values_and_wrong_ones_dropped() -> None:
    model = FakeModel(
        {
            "guest_name": {"value": "  Deniz   Örnek ", "confidence": 0.98},
            "check_in": {"value": "10.04.2027", "confidence": 0.9},  # not YYYY-MM-DD
            "nights": {"value": 10, "confidence": 1.4},
            "paid": {"value": None, "confidence": 0.2},
            "amount": {"value": {"amount": 30000, "currency": "EUR"}, "confidence": 0.95},
        }
    )
    result = extract(model, "Proof of accommodation", FIELDS, b"\xff\xd8\xffjpeg", "image/jpeg")
    assert result.values == {
        "guest_name": "Deniz Örnek",
        "check_in": None,
        "nights": 10,
        "paid": None,
        "amount": {"amount": 30000.0, "currency": "EUR"},
    }
    assert result.invalid == ["check_in"]
    assert result.confidence["nights"] == 1.0  # clamped
    assert result.cost_usd == pytest.approx((2500 * 1.00 + 300 * 5.00) / 1_000_000)
    assert "Proof of accommodation" in model.calls[0]["prompt"]


def test_a_missing_field_in_the_answer_counts_as_not_read() -> None:
    result = extract(FakeModel({}), "Document", FIELDS, b"x", "image/png")
    assert all(v is None for v in result.values.values())
    assert result.confidence == dict.fromkeys(result.confidence, 0.0)


def test_prices_cover_dated_snapshots_and_refuse_unknown_models() -> None:
    assert cost_usd("gpt-6.1-terra-2026-10-01", 1_000_000, 0) == pytest.approx(1.00)
    assert cost_usd("gpt-6.2-sol", 0, 1_000_000) == pytest.approx(10.0)
    assert cost_usd("gpt-5.4-mini", 1_000_000, 0) == pytest.approx(0.75)
    assert cost_usd("some-other-model", 10, 10) is None
    # A faster tier is a different model with a higher price, not a snapshot of Sol.
    assert cost_usd("gpt-6.1-sol-ultrafast", 10, 10) is None


def _openai(handler) -> OpenAIClient:
    return OpenAIClient("test-key", "gpt-6.1-terra", transport=httpx.MockTransport(handler))


def _completed(text: str) -> dict:
    return {
        "status": "completed",
        "model": "gpt-6.1-terra-2026-10-01",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        "usage": {"input_tokens": 1800, "output_tokens": 240},
    }


def test_the_openai_client_sends_the_image_and_a_strict_schema() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_completed('{"a": 1}'))

    reply = _openai(handler).read(
        instructions="i",
        prompt="p",
        content=b"\xff\xd8\xff",
        mime_type="image/jpeg",
        schema={"type": "object"},
        name="document_fields",
    )
    assert seen["url"].endswith("/v1/responses") and seen["auth"] == "Bearer test-key"
    body = seen["body"]
    assert body["store"] is False and body["text"]["format"]["strict"] is True
    image = body["input"][0]["content"][1]
    assert image["type"] == "input_image" and image["image_url"].startswith(
        "data:image/jpeg;base64,"
    )
    assert reply.data == {"a": 1} and (reply.input_tokens, reply.output_tokens) == (1800, 240)
    assert reply.model == "gpt-6.1-terra-2026-10-01"


def test_a_pdf_is_sent_as_a_file() -> None:
    client = _openai(lambda r: httpx.Response(200, json=_completed("{}")))
    part = client.request_body("i", "p", b"%PDF-", "application/pdf", {}, "n")["input"][0][
        "content"
    ][1]
    assert part["type"] == "input_file" and part["file_data"].startswith(
        "data:application/pdf;base64,"
    )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, json={}),
        httpx.Response(200, json={"status": "incomplete", "output": []}),
        httpx.Response(200, json={"status": "completed", "output": []}),
        httpx.Response(200, json=_completed("not json")),
    ],
)
def test_an_unusable_answer_is_a_model_error(response) -> None:
    with pytest.raises(ModelError):
        _openai(lambda r: response).read(
            instructions="i", prompt="p", content=b"x", mime_type="image/png", schema={}, name="n"
        )
