"""Field extraction: a model reads the fields of one document; the applicant confirms (FR-13).

The model proposes, the rules decide (ADR 0007). Every value the model returns is checked with the
same `normalise` as a value the applicant types; a value of the wrong form is dropped and reported,
never stored. Nothing here writes to the database: the caller shows the values to the applicant,
who saves them through the ordinary field entry.
"""

from dataclasses import dataclass, field

from app.ai.client import ModelClient
from app.ai.prices import cost_usd
from app.rules.values import Value, normalise

# extract-v1 (23 Nov 2026): first version. extract-v2: after the development trial of 23 November
# (report/data/extraction/README.md) the hints for signatures, names with titles and the employer's
# contact details were made explicit. The measurement uses extract-v2 unchanged.
PROMPT_VERSION = "extract-v2"

INSTRUCTIONS = (
    "You read one document of a Schengen visa application file and report what is printed on it. "
    "Return the value of every requested field exactly as the document shows it. If a field is not "
    "shown or cannot be read, return null for its value; never guess or infer a value from other "
    "fields. Write dates as YYYY-MM-DD. Write names as printed, keeping Turkish letters, without a "
    "title such as MR, MRS or Dr. Give a "
    "confidence from 0 to 1 for each value: how sure you are that you read it correctly."
)

_HINTS = {
    "date": "a date, written as YYYY-MM-DD",
    "int": "a whole number",
    "bool": "true or false",
    "money": "an amount and a three-letter currency code",
    "language": "a two-letter ISO 639-1 language code of the document's language, such as tr or en",
    "text": "text as printed",
}

# Hints for fields whose meaning is not obvious from their title.
FIELD_HINTS = {
    "blank_pages": "the number of visa pages without any stamp or visa",
    "translation_language": (
        "the language of an attached translation of the document; null if none is attached"
    ),
    "qr_code_readable": (
        "true if the QR code is printed undamaged and could be scanned, false if it is damaged"
    ),
    "addressed_to_consulate": "true if the letter is addressed to a consulate or embassy",
    "covers_all_schengen": "true if the insurance is valid in all Schengen states",
    "signed": (
        "true if the signature field holds a signature (a name or mark written in it, in any "
        "style); false if the field is empty"
    ),
    "employer_contact": (
        "the employer's name with its address, city, telephone or e-mail as printed, usually in "
        "the letterhead"
    ),
    "taken_on": "the date the photograph was taken",
    "pay_month": "the payment date of the salary slip",
}


@dataclass(frozen=True)
class FieldSpec:
    id: str
    type: str
    title: str


@dataclass
class Extraction:
    values: dict[str, Value | None]
    confidence: dict[str, float]
    invalid: list[str] = field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    cost_usd: float | None = None


def _value_schema(field_type: str) -> dict:
    if field_type == "money":
        return {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {"amount": {"type": "number"}, "currency": {"type": "string"}},
                    "required": ["amount", "currency"],
                    "additionalProperties": False,
                },
                {"type": "null"},
            ]
        }
    json_type = {"int": "integer", "bool": "boolean"}.get(field_type, "string")
    return {"type": [json_type, "null"]}


def schema_for(fields: list[FieldSpec]) -> dict:
    """A strict JSON schema: every field with a nullable value and a confidence."""
    properties = {
        f.id: {
            "type": "object",
            "description": f"{f.title}: {FIELD_HINTS.get(f.id, _HINTS[f.type])}",
            "properties": {"value": _value_schema(f.type), "confidence": {"type": "number"}},
            "required": ["value", "confidence"],
            "additionalProperties": False,
        }
        for f in fields
    }
    return {
        "type": "object",
        "properties": properties,
        "required": [f.id for f in fields],
        "additionalProperties": False,
    }


def prompt_for(document_title: str, fields: list[FieldSpec]) -> str:
    lines = [f"The document should be: {document_title}.", "Fields to read:"]
    lines += [f"- {f.id} ({f.title}): {FIELD_HINTS.get(f.id, _HINTS[f.type])}" for f in fields]
    return "\n".join(lines)


def extract(
    client: ModelClient,
    document_title: str,
    fields: list[FieldSpec],
    content: bytes,
    mime_type: str,
) -> Extraction:
    """Read the fields of one document; ModelError if the model gives no usable answer."""
    reply = client.read(
        instructions=INSTRUCTIONS,
        prompt=prompt_for(document_title, fields),
        content=content,
        mime_type=mime_type,
        schema=schema_for(fields),
        name="document_fields",
    )
    values: dict[str, Value | None] = {}
    confidence: dict[str, float] = {}
    invalid: list[str] = []
    for f in fields:
        item = reply.data.get(f.id) or {}
        raw = item.get("value") if isinstance(item, dict) else None
        score = item.get("confidence") if isinstance(item, dict) else None
        confidence[f.id] = (
            min(1.0, max(0.0, float(score))) if isinstance(score, int | float) else 0.0
        )
        if raw is None:
            values[f.id] = None
            continue
        try:
            values[f.id] = normalise(f.type, raw)  # type: ignore[arg-type]
        except ValueError:
            values[f.id] = None
            invalid.append(f.id)
    return Extraction(
        values=values,
        confidence=confidence,
        invalid=invalid,
        model=reply.model,
        input_tokens=reply.input_tokens,
        output_tokens=reply.output_tokens,
        seconds=reply.seconds,
        cost_usd=cost_usd(reply.model, reply.input_tokens, reply.output_tokens),
    )
