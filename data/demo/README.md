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

To load the files into the application as a demo account, with or without some of the errors
applied: `uv run python -m app.demo.load --error E06` (see `backend/README.md`). The uploaded
documents are one-page PDFs marked SAMPLE; the values come from these files.

Adding an error: copy an entry, change one value, and name the rule and code it must trigger
(the codes are listed in `backend/app/rules/engine.py`).

## Document images

`documents/` holds every document drawn as it would look on paper, marked SAMPLE, and one image
for every error that changes a value (37 images); `documents/manifest.json` lists each image with
its file, document, error and the values it shows. They are the input of field extraction and of
the model-only baseline (ADR 0007), and the demo loader uploads them. Every value the rules read is
printed on the document: the blank pages of a passport as a strip of its visa pages, a translation
as a second page, the date of a photograph on the studio's label.

```bash
cd backend && uv run python -m app.demo.render
cd ../tools/demo-documents && npm install --no-package-lock && npm run render
```

Render them again whenever a demo file or a template in `backend/app/demo/render.py` changes;
`backend/tests/test_demo_render.py` fails while the committed manifest differs from the demo files.
