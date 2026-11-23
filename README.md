# VisaAssist AI

A web application that helps visa applicants prepare their file: a checklist taken from official
sources, with the passage each requirement comes from, and a preliminary check of the uploaded
documents against those requirements.

Istanbul Bilgi University, Computer Engineering — CMPE 491/492 Senior Design Project · Furkan Özdemir

> **Status (November 2026):** fall prototype under development. The checklist, application
> files, encrypted document upload, field entry, the rule engine and the findings page work. The
> AI layer (field extraction from documents, the source-grounded assistant, monitoring of source
> changes) is planned for spring 2027; today the applicant enters the fields by hand.
>
> VisaAssist AI helps to prepare an application. It does not predict or guarantee a visa decision.

![Application page: route, readiness ring and steps](docs/design/ui/app-04-web-application.png)

## What it does
- **Checklist from official sources.** For a destination and a profile (employed, student) it
  lists the documents and rules, each with the official source, the section and the passage.
  Pilot scope: Schengen short-stay visa (C) for tourism, applied for in Türkiye, for the
  Netherlands and Norway ([ADR 0001](docs/decisions/0001-pilot-scope.md)).
- **Application files.** One file per trip, with dated steps and a readiness view.
- **Encrypted documents.** Upload per checklist item after consent; every document is encrypted
  with its own key, location data is removed from photos, and documents are deleted 30 days after
  the trip or at once on request ([ADR 0005](docs/decisions/0005-document-storage-and-consent.md)).
- **Preliminary check.** The applicant enters the key fields of each document; a rule engine
  reports missing documents and values that break a rule (dates, amounts, periods, names that
  differ between documents), each finding with its official source.
- **Turkish and English** interface, usable on a phone.

More screenshots: [docs/design/ui-design.md](docs/design/ui-design.md).

## Getting started

### The whole system with one command
Requirements: Docker.

```bash
cp .env.example .env                 # set POSTGRES_PASSWORD and DATABASE_URL to match
openssl rand -base64 32              # put the output into .env as DOCUMENT_MASTER_KEY=...
docker compose --profile app up --build
```

Open http://localhost:8080. The API container updates the tables, loads the requirement data and
a demo account, `demo@visaassist.example`, with two synthetic application files (employed for the
Netherlands, student for Norway). Its password is `DEMO_PASSWORD` from `.env`, or a random one
printed once in the log (`docker compose logs api`). The demo account is reset on every start;
set `LOAD_DEMO=false` to turn this off. To show findings, load the demo with some of its labelled
errors applied:

```bash
docker compose exec api python -m app.demo.load --list-errors
docker compose exec api python -m app.demo.load --error E06 --error S04
```

The session cookie is Secure: Chrome and Firefox accept it on http://localhost, Safari does not;
for Safari set `COOKIE_SECURE=false` in `.env`.

### Development
Requirements: Docker, [uv](https://docs.astral.sh/uv/) (Python 3.12) and Node.js 22.

```bash
cp .env.example .env                 # set POSTGRES_PASSWORD, keep DATABASE_URL in step with it
docker compose up -d                 # only PostgreSQL with pgvector

cd backend
uv sync
uv run python -m app.storage.new_key # once; put the printed line into ../.env
uv run alembic upgrade head          # create the tables
uv run python -m app.requirements.seed   # load the requirement files
uv run python -m app.demo.load           # optional: the demo account
uv run uvicorn app.main:app --reload     # API on http://127.0.0.1:8000/docs
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev                          # web client on http://localhost:5173
```

Details: [backend/README.md](backend/README.md), [frontend/README.md](frontend/README.md).
Use only synthetic documents: the prototype is not meant for real personal documents.

## Repository layout
| Path | Content |
| --- | --- |
| `backend/` | FastAPI service, PostgreSQL models and migrations, rule engine, tests |
| `frontend/` | React and TypeScript web client |
| `data/requirements/` | Document types, checklist items and rules, each citing a source |
| `data/sources.yaml`, `data/snapshots/` | Official sources and their weekly snapshots |
| `data/destinations.yaml` | Practical facts of applying to each destination, with sources |
| `data/demo/` | Synthetic demo application files with labelled errors (SAMPLE) |
| `docs/` | Requirements, design, decisions (ADR), weekly notes, related work |
| `docs/standards.md` | Standards and regulations the system applies, and how |
| `report/` | LaTeX source of the course report |

## Checks
```bash
cd backend  && uv run ruff check . && RUN_INTEGRATION=1 uv run pytest   # needs the database
cd frontend && npm run typecheck && npm test && npm run build
```
Both run in CI on every pull request.

## Documentation
- [Requirements](docs/requirements.md) · [Roadmap](docs/ROADMAP.md)
- [Official sources](docs/sources.md) · [Requirement data](data/requirements/README.md)
- [Data model](docs/design/data-model.md) · [Interface design](docs/design/ui-design.md)
- [Architecture decisions](docs/decisions/) · [Weekly progress notes](docs/weekly/)
- [Related work](docs/related-work.md) · [How it differs from a general assistant](docs/positioning.md)
- [Standards and regulations](docs/standards.md) · [Licence](LICENSE) ([ADR 0008](docs/decisions/0008-licence.md))

## Licence
All rights reserved; see [LICENSE](LICENSE). The repository is public for academic review.
