# 0002 — Architecture: start small, add components when a feature needs them
Date: 2026-10-19 · Status: Accepted

## Context
The approved proposals describe a full target architecture (React web client, FastAPI,
PostgreSQL with pgvector, Redis and Celery workers, WebSocket notifications, object storage,
Nginx, OpenAI models, OCR). The project is developed by one person with about 15 hours per
week. The fall semester delivers a working prototype in which applicants enter document fields
themselves; automatic extraction and the other AI components arrive in the spring.

## Decision
Keep from the start:
- React + TypeScript + Vite + TanStack Query + Tailwind CSS (web client)
- FastAPI + Pydantic (API), PostgreSQL + SQLAlchemy + Alembic (data), pgvector in the same
  PostgreSQL instance
- Docker Compose for local services, GitHub Actions for checks

Add when the feature that needs them is built:
- **Redis + Celery and WebSocket job updates:** spring, week B1, together with document
  extraction, the first long-running work. Fall checks run in milliseconds and need no queue.
- **Nginx reverse proxy:** spring, week B12, with the production compose file.
- **PWA support (installable app, notifications):** spring, week B12.

Simplify:
- **Object storage:** a small storage interface over a local Docker volume, with application-level
  encryption, instead of MinIO. Moving to S3-compatible storage later means replacing one class.
- **RAG pipeline:** direct pgvector queries and OpenAI embeddings instead of LlamaIndex, so the
  retrieval step stays transparent and easy to explain.
- **OCR:** Tesseract, as listed in the CMPE 491 form; PaddleOCR is not used.

Represent requirements as versioned YAML files in the repository (`data/requirements/`), each
rule citing its official source, and load them into the database with a seed step. Admin editing
in the spring builds on the same data.

## Alternatives considered
- **Full target architecture from day one:** more services to configure, test and explain before
  any user-facing feature works; high risk for a one-person schedule.
- **Polling instead of WebSocket permanently:** simpler, but the CMPE 491 form names WebSocket
  updates for long-running checks; WebSocket is therefore added with the job queue.

## Consequences
- The fall prototype runs with two services (API and database) plus the web client.
- Every added component arrives with the problem it solves, its tests and an entry here.
- Moving components to the spring adds work to an already full semester; buffer week B8 and the
  priority order in the proposal (simplify source monitoring first, then the assistant; keep the
  document pre-check and experiments) absorb overruns.
