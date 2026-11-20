# API image for `docker compose --profile app up` (see the README). Build context: the
# repository root, because the API reads data/ (requirements, sources, demo files).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend
# Dependencies first, from the lock file, so code changes do not reinstall them.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ ./
COPY data/ /app/data/

# The API does not run as root, so the code and data must be readable whatever permissions the
# files had in the working copy. Encrypted documents go to /app/storage (a volume).
RUN chmod -R a+rX /app/backend /app/data \
    && useradd --system --uid 10001 visaassist \
    && mkdir -p /app/storage && chown visaassist /app/storage
USER visaassist

EXPOSE 8000
CMD ["sh", "start.sh"]
