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

## Accounts and sessions
Design: `docs/decisions/0004-authentication.md`.

- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.
- The session is an opaque token in the HttpOnly cookie `visaassist_session`; the database keeps
  only its SHA-256. Sessions end after 7 days, or after 2 days without use.
- Every `POST`, `PUT`, `PATCH` and `DELETE` needs the header `X-Requested-With: visaassist`.
- Five failed logins within 15 minutes, per e-mail or per IP address, return `429` until the
  oldest of them is 15 minutes old.
- Administrators are created on the command line (the password is asked for, not passed):

```bash
uv run python -m app.users.create_admin --email admin@example.com
uv run python -m app.users.create_admin --email someone@example.com --reset-password
```

## Application files
`POST /applications`, `GET /applications`, `GET /applications/{id}`, `PATCH /applications/{id}`,
`DELETE /applications/{id}` (FR-05, FR-06). A file uses the requirement set that was active when
it was created; a step change is recorded as an event. Every query is limited to the logged-in
user, and another user's file answers `404`.

## Consent and documents
Design: `docs/decisions/0005-document-storage-and-consent.md`.

- `GET/POST/DELETE /consent`: upload is refused (`403`) until the current consent version is
  accepted; withdrawing consent deletes all of the user's documents.
- `POST /applications/{id}/documents` (multipart: `requirement_id`, `file`), `GET
  /applications/{id}/documents`, `GET /documents/{id}/content`, `DELETE /documents/{id}`.
- PDF, JPEG or PNG (checked from the first bytes), at most 10 MB; the item must be on the file's
  checklist.
- Each document is encrypted with its own AES-256-GCM key, wrapped with `DOCUMENT_MASTER_KEY`,
  and stored under a random name in `storage/` (not committed). The API does not start without
  the key. Losing the key makes the stored documents unreadable.
- Known limitation: while an upload is being received, the web framework may buffer a large
  file in a temporary file of the operating system before it is encrypted; it is removed when the
  request ends.

```bash
uv run python -m app.storage.new_key        # once; put the printed line into ../.env
uv run python -m app.storage.cleanup        # daily: expired documents and orphaned files
```

## Field entry and checks
- `GET/PUT /documents/{id}/fields`: the fields to enter for a document and their values (FR-08).
  Values are encrypted with the document's own key.
- `GET /applications/{id}/check`: missing documents and the state of every rule on the entered
  values: `passed`, `failed`, `incomplete` (a value is missing) or `skipped` (its document is not
  uploaded). Computed on request by the rule engine (`app/rules/engine.py`, pure functions).
- `POST/GET /applications/{id}/checks`: keep a check and list the kept ones. A kept check holds
  rule states and where each issue is, never the entered values.
- `GET /destinations?lang=tr`: practical facts of applying to each destination, each with its
  official source (`data/destinations.yaml`).

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
