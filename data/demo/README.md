# Demo application files (SAMPLE)

Synthetic application files for the demo and for the fall success criterion: *every injected
error of the supported types is reported, and the error-free file gets no finding*
(`docs/requirements.md`, section 6). Every person, number and organisation in them is invented.

| File | Profile | Destination | Labelled errors |
| --- | --- | --- | --- |
| `employed-nl.yaml` | employed | Netherlands | 10 (E01–E10) |
| `student-no.yaml` | student | Norway | 7 (S01–S07) |

Each file has documents with field values that satisfy every rule of its destination and profile,
and a list of `errors`. An error changes one thing (removes a document or sets one value) and
names the finding it must produce: a missing checklist item, or a rule with its issue code.

```bash
cd backend
uv run python -m app.demo.evaluate     # Markdown table; exit status 1 if an error is missed
```

The command checks the clean file first, then applies each error alone. An error counts as
*detected* when exactly the labelled finding appears, and as *detected with extra findings* when
other rules react as well. `backend/tests/test_demo.py` runs the same check in CI.

Adding an error: copy an entry, change one value, and name the rule and code it must trigger
(the codes are listed in `backend/app/rules/engine.py`).
