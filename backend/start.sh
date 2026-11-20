#!/bin/sh
# Start of the API container: update the tables, load the requirement data, load the demo
# account if LOAD_DEMO=true (it replaces the demo account's files on every start), then serve.
set -e
alembic upgrade head
python -m app.requirements.seed
if [ "${LOAD_DEMO:-false}" = "true" ]; then
  python -m app.demo.load
fi
# The web container is the only client; it forwards the visitor's address for login throttling.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
