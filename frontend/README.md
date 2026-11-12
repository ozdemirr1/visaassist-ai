# VisaAssist AI — Web client

React + TypeScript + Vite, TanStack Query, Tailwind CSS (ADR 0002). One responsive web
application in Turkish and English (NFR-04, NFR-10); all interface text is in
`src/locales/tr.json` and `src/locales/en.json`.

## Run locally
The client calls the API under `/api` on its own origin; in development Vite forwards `/api`
to the FastAPI server on port 8000, so the session cookie stays first-party (ADR 0004).

```bash
# terminal 1: database and API
cd ~/visaassist-ai && docker compose up -d
cd backend && uv run uvicorn app.main:app --reload

# terminal 2: web client
cd ~/visaassist-ai/frontend
npm install          # first time, and after package.json changes
npm run dev          # http://localhost:5173
```

Safari refuses `Secure` cookies on `http://localhost` (Chrome accepts them): for development,
set `COOKIE_SECURE=false` in the repository-root `.env` and restart the API. Never in production.

## Checks
```bash
npm run typecheck
npm test
npm run build
```

## Pages
| Path | Content |
| --- | --- |
| `/` | Destination and profile → checklist with the official source of every item (FR-02, FR-03) |
| `/login`, `/register` | Log in, create an account |
| `/destinations` | Where, when and how to apply, each fact with its official source |
| `/applications` | The user's application files |
| `/applications/new` | Wizard: destination, profile, trip dates |
| `/applications/:id` | Route, readiness, steps, checklist with upload, field entry and rule states |
| `/applications/:id/findings` | Preliminary check: missing documents, problems, kept checks |
