# Demo document images

Renders every document of the demo files (`data/demo/*.yaml`) as an image marked SAMPLE, plus one
image for every labelled error that changes a value. The images are the input of field extraction
and of the model-only baseline (ADR 0007); `data/demo/documents/manifest.json` lists each image
with its file, document, error and the values it shows.

```bash
cd backend && uv run python -m app.demo.render       # HTML pages and manifest
cd ../tools/demo-documents && npm install --no-package-lock && npm run render
```

The images are committed, so the extraction and the evaluation always read the same pixels.
Render them again only when a demo file or a template changes.
