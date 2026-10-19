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

## Checks
```bash
uv run pytest                            # unit tests (no database needed)
RUN_INTEGRATION=1 uv run pytest          # also database tests (needs docker compose up)
uv run ruff check .
uv run ruff format --check .
```
