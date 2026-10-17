# VisaAssist AI — Backend

FastAPI service for the VisaAssist AI web application.

## Requirements
- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 and dependencies)

## Run locally
```bash
cd backend
uv sync                                  # installs Python 3.12 + dependencies, writes uv.lock
uv run uvicorn app.main:app --reload     # http://127.0.0.1:8000/health, docs at /docs
```

## Checks
```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
