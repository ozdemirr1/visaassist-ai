# Figure sources

`design-arch.html` draws `../design-arch.png` (architecture, Chapter 4). Render it at twice the
size with Playwright, from this folder:

```bash
node -e "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1600,height:830},deviceScaleFactor:2});await p.goto('file://'+process.cwd()+'/design-arch.html');await p.screenshot({path:'../design-arch.png'});await b.close()})()"
```

`design-er.png` (data model) was drawn from the Mermaid diagram in `docs/design/data-model.md`.
The `shot-*.png` screenshots come from `report/screenshots/capture.mjs`.
