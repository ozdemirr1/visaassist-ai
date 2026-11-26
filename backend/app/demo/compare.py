"""Compare the model alone with the model plus the rule engine on the demo files (report, 6.2).

    uv run python -m app.demo.compare --model gpt-6.2-sol --runs 3 \\
        --out ../report/data/comparison/2026-11-26_gpt-6.2-sol.jsonl
    uv run python -m app.demo.compare --cases employed-nl:clean --runs 1     # a quick look

Cases: each demo file as it is (no error), and each labelled error applied alone: 2 + 17 = 19.
The same rendered SAMPLE images go to both systems.

- **Model alone**: one call per case with all document images of the file and the facts the
  system also has (destination, purpose, profile, trip and application dates), asking for every
  problem, each tied to one document type. No rule, checklist or source text is given: this is
  what a general assistant gets from an applicant.
- **Model + rules**: the model reads the fields of each document (`extract-v2`, the same call as
  "Read from document"); the rule engine then checks the values, as the application does.

An error counts as found by the model alone when it reports a problem on the document the error
changed (or names the missing document's type). This is lenient: whether its description is right
is not checked automatically, and the raw answers are kept for reading. An error counts as found
by the rules when the labelled rule fails with the labelled code (or the item is missing). Every
other problem or finding is a false alarm. Calls are logged in `model_calls` (purpose "compare")
and stop when the month's budget is used up.
"""

import argparse
import base64
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app import models
from app.ai import extraction
from app.ai.client import ModelError, OpenAIClient
from app.ai.prices import cost_usd
from app.api.extraction import month_cost
from app.config import get_settings
from app.db import get_engine
from app.demo.files import DemoError, DemoFile, changed, load_all
from app.demo.load import IMAGE_DIR
from app.requirements.loader import RequirementData, load_requirement_data
from app.rules import engine

MANIFEST = IMAGE_DIR / "manifest.json"
PROMPT_VERSION = "compare-v1"
PURPOSES = {"NL": "Netherlands", "NO": "Norway"}

ALONE_INSTRUCTIONS = (
    "You help an applicant in Türkiye check a Schengen short-stay (type C) visa application for "
    "tourism before it is submitted. You receive the images of the documents the applicant has "
    "prepared. Report every problem that could lead the consulate to refuse the application or "
    "ask for more: a document that is missing, a date or period that does not fit the trip or the "
    "application date, a value that is too low or too old, names or numbers that do not agree "
    "between documents, a missing signature or translation, and similar. Tie each problem to the "
    "type of the document it concerns. If the file has no problem, return an empty list. Report "
    "only problems you can see or that follow from the trip; do not list general advice."
)


@dataclass
class Case:
    demo: DemoFile
    error: DemoError | None

    @property
    def name(self) -> str:
        return f"{self.demo.id}:{self.error.id if self.error else 'clean'}"


@dataclass
class Outcome:
    run: int
    system: str  # "model alone" | "model + rules"
    case: str
    error: str | None
    expected: str | None  # the document type the error concerns, or the missing item
    found: bool | None  # None for a clean case
    false_alarms: list[str] = field(default_factory=list)
    incomplete: list[str] = field(default_factory=list)  # rules the engine could not decide
    answer: object = None  # the model's problems, or the engine's findings
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    cost_usd: float = 0.0
    failure: str | None = None


def cases(demos: list[DemoFile]) -> list[Case]:
    return [Case(d, None) for d in demos] + [Case(d, e) for d in demos for e in d.errors]


def images_for(case: Case, manifest: list[dict]) -> list[tuple[object, str]]:
    """(document, image file) for every document of the case; the error's image where it has one."""
    by_key = {(e["file"], e["document"], e["error"]): e["image"] for e in manifest}
    error_id = case.error.id if case.error else None
    documents = changed(case.demo, [case.error.change] if case.error else [])
    result = []
    for document in documents:
        image = (
            by_key.get((case.demo.id, document.id, error_id))
            or by_key[(case.demo.id, document.id, None)]
        )
        result.append((document, image))
    return result


def concerned_type(case: Case) -> str | None:
    """The document type the case's error concerns."""
    if case.error is None:
        return None
    change = case.error.change
    if change.set is not None:
        return next(d.type for d in case.demo.documents if d.id == change.set.document)
    removed = next(d for d in case.demo.documents if d.id == change.remove)
    return removed.type


def document_types(case: Case, data: RequirementData) -> list[str]:
    items = data.ruleset(case.demo.destination).checklist(case.demo.profile)
    return sorted({r.document for r in items})


# Model alone


def alone_schema(types: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "problems": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "document_type": {"type": "string", "enum": [*types, "other"]},
                        "problem": {"type": "string"},
                    },
                    "required": ["document_type", "problem"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["problems"],
        "additionalProperties": False,
    }


def alone_prompt(case: Case, data: RequirementData, labels: list[str]) -> str:
    trip = case.demo.trip
    types = ", ".join(
        f"{t} ({data.catalog.document(t).title.en})" for t in document_types(case, data)
    )
    return "\n".join(
        [
            f"Destination: {PURPOSES[case.demo.destination]}. Purpose: tourism. "
            f"Applicant: {case.demo.profile}.",
            f"Trip: {trip.start.isoformat()} to {trip.end.isoformat()}. "
            f"Application date: {trip.application_date.isoformat()}.",
            f"Document types to use in your answer: {types}, or other.",
            "The images follow in this order: " + "; ".join(labels) + ".",
        ]
    )


def alone_request(client: OpenAIClient, case: Case, data: RequirementData, images) -> dict:
    labels = [f"image {i + 1}" for i in range(len(images))]
    content = [{"type": "input_text", "text": alone_prompt(case, data, labels)}]
    for _, image in images:
        encoded = base64.b64encode((IMAGE_DIR / image).read_bytes()).decode()
        content.append(
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{encoded}",
                "detail": "auto",
            }
        )
    return {
        "model": client.model,
        "instructions": ALONE_INSTRUCTIONS,
        "input": [{"role": "user", "content": content}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "problems",
                "schema": alone_schema(document_types(case, data)),
                "strict": True,
            }
        },
        "store": False,
    }


def call_raw(client: OpenAIClient, body: dict) -> tuple[dict, str, int, int, float]:
    """POST a prepared body; the same checks as `OpenAIClient.read`."""
    started = time.monotonic()
    response = client._http.post("/responses", json=body)
    seconds = time.monotonic() - started
    if response.status_code != 200:
        raise ModelError(f"The model service answered {response.status_code}.")
    payload = response.json()
    if payload.get("status") != "completed":
        raise ModelError("The model did not finish its answer.")
    texts = [
        part.get("text", "")
        for item in payload.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    ]
    if not texts:
        raise ModelError("The model gave no answer.")
    usage = payload.get("usage") or {}
    return (
        json.loads(texts[0]),
        payload.get("model", client.model),
        int(usage.get("input_tokens", 0)),
        int(usage.get("output_tokens", 0)),
        seconds,
    )


def score_alone(case: Case, data: RequirementData, problems: list[dict], outcome: Outcome) -> None:
    target = concerned_type(case)
    hits = [p for p in problems if target is not None and p["document_type"] == target]
    outcome.expected = target
    outcome.found = None if case.error is None else bool(hits)
    outcome.false_alarms = [
        f"{p['document_type']}: {p['problem']}" for p in problems if p not in hits
    ]
    outcome.answer = problems


# Model + rules


def specs_for(data: RequirementData, case: Case, document_type: str) -> list[extraction.FieldSpec]:
    """The fields the field form asks for: the language fields only where a rule reads them."""
    specs = [
        extraction.FieldSpec(f.id, f.type, f.title.en)
        for f in data.catalog.document(document_type).fields
    ]
    rules = data.ruleset(case.demo.destination).rules_for(case.demo.profile)
    asks_language = any(
        r.check.kind == "translation_present"
        and document_type not in getattr(r.check, "exempt", [])
        for r in rules
    )
    if asks_language:
        specs += [
            extraction.FieldSpec(f.id, f.type, f.title.en) for f in data.catalog.common_fields
        ]
    return specs


def score_rules(case: Case, data: RequirementData, documents, outcome: Outcome) -> None:
    ruleset = data.ruleset(case.demo.destination)
    required = {r.id: r.document for r in ruleset.checklist(case.demo.profile)}
    trip = engine.Trip(case.demo.trip.start, case.demo.trip.end, case.demo.trip.application_date)
    results = engine.evaluate(ruleset.rules_for(case.demo.profile), documents, trip)
    missing = engine.missing_documents(required, documents)
    failed = {r.rule_id: [i.code for i in r.issues] for r in results if r.status == "failed"}
    outcome.incomplete = [r.rule_id for r in results if r.status == "incomplete"]
    outcome.answer = {"missing": missing, "failed": failed}
    expect = case.error.expect if case.error else None
    if expect is None:
        outcome.found = None
        outcome.false_alarms = missing + [f"{rule}: {','.join(c)}" for rule, c in failed.items()]
        return
    if expect.missing is not None:
        outcome.expected = expect.missing
        outcome.found = expect.missing in missing
        outcome.false_alarms = [m for m in missing if m != expect.missing] + [
            f"{rule}: {','.join(c)}" for rule, c in failed.items()
        ]
    else:
        outcome.expected = f"{expect.rule}: {expect.code}"
        outcome.found = expect.code in failed.get(expect.rule or "", [])
        outcome.false_alarms = missing + [
            f"{rule}: {','.join(c)}" for rule, c in failed.items() if rule != expect.rule
        ]


# Running


class Runner:
    def __init__(self, client: OpenAIClient, session: Session, budget: float) -> None:
        self.client, self.session, self.budget = client, session, budget

    def over_budget(self) -> bool:
        return month_cost(self.session, datetime.now(UTC)) >= self.budget

    def log(
        self,
        document_type: str | None,
        model: str,
        tokens: tuple[int, int],
        seconds: float,
        cost: float | None,
        ok: bool,
        prompt: str,
    ) -> None:
        self.session.add(
            models.ModelCall(
                user_id=None,
                purpose="compare",
                document_type_id=document_type,
                model=model,
                prompt_version=prompt,
                input_tokens=tokens[0],
                output_tokens=tokens[1],
                cost_usd=cost if ok else 0.0,
                seconds=seconds,
                succeeded=ok,
                created_at=datetime.now(UTC),
            )
        )
        self.session.commit()


def run_alone(runner: Runner, case: Case, data, manifest, number: int) -> Outcome:
    outcome = Outcome(
        number, "model alone", case.name, case.error.id if case.error else None, None, None
    )
    images = images_for(case, manifest)
    try:
        answer, model, tin, tout, seconds = call_raw(
            runner.client, alone_request(runner.client, case, data, images)
        )
    except (ModelError, json.JSONDecodeError) as error:
        outcome.failure = str(error)
        runner.log(None, runner.client.model, (0, 0), 0.0, 0.0, False, PROMPT_VERSION)
        return outcome
    cost = cost_usd(model, tin, tout) or 0.0
    outcome.input_tokens, outcome.output_tokens = tin, tout
    outcome.seconds, outcome.cost_usd = seconds, cost
    runner.log(None, model, (tin, tout), seconds, cost, True, PROMPT_VERSION)
    score_alone(case, data, answer.get("problems", []), outcome)
    return outcome


def run_rules(
    runner: Runner,
    case: Case,
    data,
    manifest,
    number: int,
    cache: dict[str, extraction.Extraction | None],
) -> Outcome:
    outcome = Outcome(
        number, "model + rules", case.name, case.error.id if case.error else None, None, None
    )
    documents = []
    for document, image in images_for(case, manifest):
        if image not in cache:  # each image is read once per run
            title = data.catalog.document(document.type).title.en
            try:
                cache[image] = extraction.extract(
                    runner.client,
                    title,
                    specs_for(data, case, document.type),
                    (IMAGE_DIR / image).read_bytes(),
                    "image/jpeg",
                )
                result = cache[image]
                runner.log(
                    document.type,
                    result.model,
                    (result.input_tokens, result.output_tokens),
                    result.seconds,
                    result.cost_usd,
                    True,
                    extraction.PROMPT_VERSION,
                )
            except ModelError as error:
                cache[image] = None
                outcome.failure = f"{image}: {error}"
                runner.log(
                    document.type,
                    runner.client.model,
                    (0, 0),
                    0.0,
                    0.0,
                    False,
                    extraction.PROMPT_VERSION,
                )
        result = cache[image]
        if result is None:
            continue
        outcome.input_tokens += result.input_tokens
        outcome.output_tokens += result.output_tokens
        outcome.seconds += result.seconds  # as if the case were read alone
        outcome.cost_usd += result.cost_usd or 0.0
        values = {k: v for k, v in result.values.items() if v is not None}
        documents.append(engine.Document(id=document.id, type=document.type, values=values))
    score_rules(case, data, documents, outcome)
    return outcome


def summary(outcomes: list[Outcome], errors: int, clean: int) -> str:
    lines = []
    by_system: dict[str, list[Outcome]] = defaultdict(list)
    for o in outcomes:
        by_system[o.system].append(o)
    for system, rows in by_system.items():
        runs = sorted({o.run for o in rows})
        found = [sum(bool(o.found) for o in rows if o.run == r and o.error) for r in runs]
        clean_alarms = [
            sum(len(o.false_alarms) for o in rows if o.run == r and not o.error) for r in runs
        ]
        error_alarms = [
            sum(len(o.false_alarms) for o in rows if o.run == r and o.error) for r in runs
        ]
        failures = sum(o.failure is not None for o in rows)
        seconds = sum(o.seconds for o in rows) / max(len(rows), 1)
        cost = sum(o.cost_usd for o in rows) / max(len(runs), 1)
        lines += [
            f"{system}:",
            f"  errors found per run: {found} of {errors}",
            f"  false alarms on the {clean} clean files per run: {clean_alarms}",
            f"  false alarms in the error cases per run: {error_alarms}",
            f"  failed calls: {failures} · {seconds:.1f} s per case · USD {cost:.3f} per run",
        ]
        missed = defaultdict(int)
        for o in rows:
            if o.error and not o.found:
                missed[o.error] += 1
        if missed:
            lines.append("  missed: " + ", ".join(f"{e} ({n}x)" for e, n in sorted(missed.items())))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", help="default: EXTRACTION_MODEL")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument(
        "--cases",
        action="append",
        default=[],
        metavar="FILE:ERROR",
        help="only these cases, e.g. employed-nl:clean or student-no:S03",
    )
    parser.add_argument("--system", choices=["alone", "rules", "both"], default="both")
    parser.add_argument("--out", type=Path, help="write one JSON line per run, system and case")
    args = parser.parse_args(argv)

    settings = get_settings()
    if not settings.openai_api_key:
        print("OPENAI_API_KEY is not set in .env.", file=sys.stderr)
        return 1
    model = args.model or settings.extraction_model
    if cost_usd(model, 0, 0) is None:
        print(f"No known price for {model}; add it to app/ai/prices.py first.", file=sys.stderr)
        return 1
    data = load_requirement_data()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selected = cases(load_all())
    if args.cases:
        selected = [c for c in selected if c.name in args.cases]
    errors = sum(c.error is not None for c in selected)
    clean = len(selected) - errors

    client = OpenAIClient(settings.openai_api_key, model, settings.openai_base_url, timeout=240)
    outcomes: list[Outcome] = []
    with Session(get_engine()) as session:
        runner = Runner(client, session, settings.model_monthly_budget_usd)
        for number in range(1, args.runs + 1):
            cache: dict[str, extraction.Extraction | None] = {}
            for case in selected:
                if runner.over_budget():
                    print("The month's model budget is used up; stopping.", file=sys.stderr)
                    break
                if args.system in ("alone", "both"):
                    outcomes.append(run_alone(runner, case, data, manifest, number))
                if args.system in ("rules", "both"):
                    outcomes.append(run_rules(runner, case, data, manifest, number, cache))
                for o in outcomes[-2 if args.system == "both" else -1 :]:
                    mark = "-" if o.found is None else ("found" if o.found else "MISSED")
                    print(
                        f"[{number}] {o.system:13} {o.case:16} {mark:7} "
                        f"alarms {len(o.false_alarms)}",
                        file=sys.stderr,
                    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as out:
            for o in outcomes:
                out.write(json.dumps(asdict(o), ensure_ascii=False, default=str) + "\n")
    print(summary(outcomes, errors, clean))
    return 0


if __name__ == "__main__":
    sys.exit(main())
