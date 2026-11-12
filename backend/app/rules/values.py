"""The stored form of a field value, by field type (FR-08, docs/design/data-model.md).

text → str · date → ISO date string · int → int · bool → bool ·
money → {"amount": number, "currency": "EUR"} · language → two-letter code.
"""

import re
from datetime import date

from app.requirements.schema import FieldType

Value = str | int | bool | dict[str, object]

MAX_TEXT = 200
MAX_INT = 10_000
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_LANGUAGE = re.compile(r"^[a-z]{2}$")


def normalise(field_type: FieldType, raw: object) -> Value:
    """The stored form of a value sent by the client; ValueError says what is wrong with it."""
    if field_type == "text":
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("expected text")
        text = " ".join(raw.split())
        if len(text) > MAX_TEXT:
            raise ValueError(f"at most {MAX_TEXT} characters")
        return text
    if field_type == "date":
        if not isinstance(raw, str):
            raise ValueError("expected a date as YYYY-MM-DD")
        try:
            return date.fromisoformat(raw).isoformat()
        except ValueError as error:
            raise ValueError("expected a date as YYYY-MM-DD") from error
    if field_type == "int":
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= MAX_INT:
            raise ValueError(f"expected a whole number from 0 to {MAX_INT}")
        return raw
    if field_type == "bool":
        if not isinstance(raw, bool):
            raise ValueError("expected true or false")
        return raw
    if field_type == "money":
        if not isinstance(raw, dict):
            raise ValueError("expected an amount and a currency")
        amount, currency = raw.get("amount"), raw.get("currency")
        if isinstance(amount, bool) or not isinstance(amount, int | float) or amount <= 0:
            raise ValueError("expected an amount above zero")
        if not isinstance(currency, str) or not _CURRENCY.match(currency):
            raise ValueError("expected a three-letter currency code such as EUR")
        return {"amount": float(amount), "currency": currency}
    if field_type == "language":
        if not isinstance(raw, str) or not _LANGUAGE.match(raw):
            raise ValueError("expected a two-letter language code such as tr")
        return raw
    raise ValueError(f"unknown field type {field_type}")
