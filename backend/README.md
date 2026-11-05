# VisaAssist AI — Backend

FastAPI service for the VisaAssist AI web application.

## Requirements
- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 and dependencies)
- Docker (for the local PostgreSQL database)

## Run locally
```bash
cp .env.example .env                     # once, from the repository root; edit the password
docker compose up -d                     # from the repository root: starts PostgreSQL (pgvector)
cd backend
uv sync                                  # installs Python 3.12 + dependencies
uv run uvicorn app.main:app --reload     # http://127.0.0.1:8000/docs
```

Endpoints:
- `GET /health` — liveness: the API process is up.
- `GET /health/ready` — readiness: the API can reach the database (`503` if not).
- `GET /checklist?destination=NL&profile=employed&lang=tr` — documents and rules for one
  destination and profile, each with the official source passage it comes from. `404` for an
  unknown destination, `503` if no requirement set has been loaded.

## Database and requirement data
```bash
uv run alembic upgrade head                 # create or update the tables
uv run python -m app.requirements.seed      # load data/requirements/ as a requirement set
```

The seed command identifies a requirement set by the SHA-256 of `data/requirements/*.yaml` and
`data/sources.yaml`: running it again on unchanged files changes nothing; after a change it
loads a new set and makes it the active one (older sets are kept, so earlier checks stay
explainable). Design: `docs/design/data-model.md`.

New migration after changing `app/models.py`:
```bash
uv run alembic revision --autogenerate -m "short description"   # then review the file
```

## Checks
```bash
uv run pytest                            # unit tests (no database needed)
RUN_INTEGRATION=1 uv run pytest          # also database, seed and checklist tests (docker compose up)
uv run ruff check .
uv run ruff format --check .
```

## Official source snapshots
The sources behind the requirements are listed in `data/sources.yaml` (inventory and notes:
`docs/sources.md`). To capture a snapshot of every source, run weekly from `backend/`:

```bash
uv run python -m app.sources.snapshot                      # all sources
uv run python -m app.sources.snapshot --only nl-apply-tr   # one source
```

A file is written to `data/snapshots/<source-id>/` only when the content changed; every attempt
is appended to `data/snapshots/manifest.jsonl`. The command exits with status 1 if a source
could not be fetched.
