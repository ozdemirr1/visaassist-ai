# Report screenshots

`capture.mjs` takes the report's screenshots (`report/figures/shot-*.png`) from the running
system with the synthetic demo account, at a fixed window size, so they can be taken again
whenever the interface changes.

```bash
docker compose --profile app up -d                      # from the repository root
docker compose exec api python -m app.demo.load --error E06 --error S04
cd report/screenshots
npm install --no-package-lock                           # playwright-core only; uses your Chrome
DEMO_PASSWORD='…' npm run capture                       # SHOT_LANG=tr for Turkish screens
```

The consent screenshot registers a new synthetic account (`screens-<time>@visaassist.example`)
because the demo account has already consented.
