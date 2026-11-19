"""Run the rule engine on the demo files and compare its findings with the labelled errors.

    uv run python -m app.demo.evaluate            # table in Markdown, exit status 1 on a miss

For each demo file: the clean file must give no finding; then each error is applied alone and
must give exactly the finding its label names (fall success criterion, docs/requirements.md).
"""

import sys

from app.demo.files import ErrorResult, evaluate_error, findings, load_all
from app.requirements.loader import load_requirement_data


def main() -> int:
    data = load_requirement_data()
    demos = load_all()
    rows: list[ErrorResult] = []
    clean_ok = True
    print("| File | Clean file | Rules checked |")
    print("| --- | --- | --- |")
    for demo in demos:
        clean = findings(demo, data)
        rules = len(data.ruleset(demo.destination).rules_for(demo.profile))
        state = "no finding" if clean.is_empty() else f"UNEXPECTED: {clean}"
        clean_ok &= clean.is_empty()
        print(f"| {demo.id} | {state} | {rules} |")
        rows.extend(evaluate_error(demo, error, data) for error in demo.errors)

    print()
    print("| File | Error | Kind | Expected finding | Outcome |")
    print("| --- | --- | --- | --- | --- |")
    for row in rows:
        expect = row.error.expect
        label = f"missing {expect.missing}" if expect.missing else f"{expect.rule} ({expect.code})"
        print(f"| {row.demo} | {row.error.id} | {row.error.kind} | {label} | {row.outcome} |")

    detected = sum(1 for r in rows if r.outcome != "missed")
    exact = sum(1 for r in rows if r.outcome == "detected")
    print()
    print(f"Errors detected: {detected} of {len(rows)}; without extra findings: {exact}.")
    return 0 if clean_ok and detected == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
