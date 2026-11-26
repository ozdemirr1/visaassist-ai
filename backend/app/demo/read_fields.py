"""Read the fields of the rendered demo documents with the model and score them (FR-13, ADR 0007).

    uv run python -m app.demo.read_fields                  # the 23 clean images, default model
    uv run python -m app.demo.read_fields --all            # also the 14 images with an error
    uv run python -m app.demo.read_fields --model gpt-6.2-sol --runs 3 --out ../report/data/x.jsonl

Each image of `data/demo/documents/manifest.json` is sent to the model with the fields of its
document type, and every value the manifest states is compared with what the model returned. A
value counts as correct when the rule engine would treat it as the same value: names without case,
Turkish letters or order, as `names_match` compares them; dates, numbers and amounts exactly.

Only synthetic SAMPLE images are sent. Every call is logged in `model_calls` with the purpose
"trial", so it counts against the month's budget, and the run stops before a call once the budget
is used up. The result is one JSON line per image and run, and a summary on the terminal.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app import models
from app.ai import extraction
from app.ai.client import ModelClient, ModelError, OpenAIClient
from app.ai.prices import cost_usd
from app.api.extraction import month_cost
from app.config import get_settings
from app.db import get_engine
from app.demo.load import IMAGE_DIR
from app.requirements.loader import RequirementData, load_requirement_data
from app.rules.engine import normalise_code, normalise_name
from app.rules.values import Value, normalise

MANIFEST = IMAGE_DIR / "manifest.json"


@dataclass
class FieldResult:
    field: str
    expected: Value
    read: Value | None
    correct: bool
    confidence: float


@dataclass
class ImageResult:
    image: str
    document_type: str
    error: str | None
    run: int
    model: str
    prompt_version: str
    fields: list[FieldResult] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)  # read where the document states nothing
    invalid: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    cost_usd: float | None = None
    failure: str | None = None


def same(field_type: str, expected: Value, read: Value | None) -> bool:
    """Whether the rule engine would treat the two values as the same."""
    if read is None:
        return False
    if field_type == "text":  # a name as names_match compares it, a number as values_match does
        return normalise_name(str(expected)) == normalise_name(str(read)) or normalise_code(
            str(expected)
        ) == normalise_code(str(read))
    if field_type == "money":
        assert isinstance(expected, dict) and isinstance(read, dict)
        return (
            abs(float(expected["amount"]) - float(read["amount"])) < 0.01  # type: ignore[arg-type]
            and expected["currency"] == read["currency"]
        )
    return expected == read


def specs_for(data: RequirementData, document_type: str, truth: dict) -> list[extraction.FieldSpec]:
    """The fields of the type, and the common language fields where the manifest states them."""
    specs = [
        extraction.FieldSpec(f.id, f.type, f.title.en)
        for f in data.catalog.document(document_type).fields
    ]
    specs += [
        extraction.FieldSpec(f.id, f.type, f.title.en)
        for f in data.catalog.common_fields
        if f.id in truth
    ]
    return specs


def score(
    data: RequirementData, entry: dict, result: extraction.Extraction, image: ImageResult
) -> None:
    truth = {k: v for k, v in entry["values"].items() if v is not None}
    for spec in specs_for(data, entry["type"], truth):
        read = result.values.get(spec.id)
        if spec.id not in truth:
            if read is not None:
                image.unexpected.append(spec.id)
            continue
        expected = normalise(spec.type, truth[spec.id])  # type: ignore[arg-type]
        image.fields.append(
            FieldResult(
                spec.id,
                expected,
                read,
                same(spec.type, expected, read),
                result.confidence.get(spec.id, 0.0),
            )
        )


def log_call(session: Session, image: ImageResult) -> None:
    session.add(
        models.ModelCall(
            user_id=None,
            purpose="trial",
            document_type_id=image.document_type,
            model=image.model,
            prompt_version=image.prompt_version,
            input_tokens=image.input_tokens,
            output_tokens=image.output_tokens,
            cost_usd=image.cost_usd if image.failure is None else 0.0,
            seconds=image.seconds,
            succeeded=image.failure is None,
            created_at=datetime.now(UTC),
        )
    )
    session.commit()


def run(
    client: ModelClient,
    session: Session,
    entries: list[dict],
    runs: int,
    budget: float,
    data: RequirementData,
) -> list[ImageResult]:
    results: list[ImageResult] = []
    model = getattr(client, "model", "?")
    for number in range(1, runs + 1):
        for entry in entries:
            if month_cost(session, datetime.now(UTC)) >= budget:
                print("The month's model budget is used up; stopping.", file=sys.stderr)
                return results
            image = ImageResult(
                entry["image"],
                entry["type"],
                entry["error"],
                number,
                model,
                extraction.PROMPT_VERSION,
            )
            truth = {k: v for k, v in entry["values"].items() if v is not None}
            title = data.catalog.document(entry["type"]).title.en
            content = (IMAGE_DIR / entry["image"]).read_bytes()
            try:
                result = extraction.extract(
                    client, title, specs_for(data, entry["type"], truth), content, "image/jpeg"
                )
            except ModelError as error:
                image.failure = str(error)
            else:
                image.model = result.model
                image.input_tokens, image.output_tokens = result.input_tokens, result.output_tokens
                image.seconds, image.cost_usd = result.seconds, result.cost_usd
                image.invalid = result.invalid
                score(data, entry, result, image)
            log_call(session, image)
            results.append(image)
            wrong = [f.field for f in image.fields if not f.correct]
            status = image.failure or (f"wrong: {', '.join(wrong)}" if wrong else "all correct")
            print(f"[{number}] {entry['image']}: {status}", file=sys.stderr)
    return results


def summary(results: list[ImageResult]) -> str:
    fields = [f for r in results for f in r.fields]
    correct = sum(f.correct for f in fields)
    wrong: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for r in results:
        for f in r.fields:
            if not f.correct:
                key = f"{r.document_type}.{f.field}"
                wrong[key] += 1
                if len(examples[key]) < 2:
                    examples[key].append(f"expected {f.expected!r}, read {f.read!r}")
    cost = sum(r.cost_usd or 0.0 for r in results)
    seconds = sum(r.seconds for r in results)
    lines = [
        f"images: {len(results)} · failed calls: {sum(r.failure is not None for r in results)}",
        f"fields correct: {correct} / {len(fields)}"
        + (f" ({100 * correct / len(fields):.1f}%)" if fields else ""),
        f"values read where the document states none: {sum(len(r.unexpected) for r in results)}",
        f"cost: USD {cost:.4f} · average {seconds / max(len(results), 1):.1f} s per image",
    ]
    for key, count in wrong.most_common():
        lines.append(f"  wrong {count}x {key}: {'; '.join(examples[key])}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", help="default: EXTRACTION_MODEL")
    parser.add_argument("--all", action="store_true", help="also the images with an error")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="IMAGE",
        help="only this image file (repeatable)",
    )
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--out", type=Path, help="write one JSON line per image and run")
    args = parser.parse_args(argv)

    settings = get_settings()
    if not settings.openai_api_key:
        print("OPENAI_API_KEY is not set in .env.", file=sys.stderr)
        return 1
    model = args.model or settings.extraction_model
    if cost_usd(model, 0, 0) is None:
        print(f"No known price for {model}; add it to app/ai/prices.py first.", file=sys.stderr)
        return 1
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = [e for e in entries if args.all or e["error"] is None]
    if args.only:
        entries = [e for e in entries if e["image"] in args.only]
    client = OpenAIClient(settings.openai_api_key, model, settings.openai_base_url)
    with Session(get_engine()) as session:
        results = run(
            client,
            session,
            entries,
            args.runs,
            settings.model_monthly_budget_usd,
            load_requirement_data(),
        )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as out:
            for r in results:
                out.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    print(summary(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
