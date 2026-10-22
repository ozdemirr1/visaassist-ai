# Week 5 — 2026-10-19 to 2026-10-25

Fall semester week 5. Prepared for the advisor meeting on Friday, 23 October 2026.

## Completed this week
- **Database infrastructure:** PostgreSQL 17 with pgvector via Docker Compose; settings from `.env`; `GET /health/ready` returns 503 when the database is unreachable; database integration tests run in CI (#7, PR #8).
- **Decisions recorded:** ADR 0001 pilot scope (Netherlands, Schengen short-stay tourism, employed and student applicants); ADR 0002 architecture (components added when a feature needs them); roadmap aligned with the work plan (#9, PR #10).
- **Requirements specification:** 22 functional and 9 non-functional requirements, constraints, success criteria for fall and spring (#11, PR #12).
- **Project management:** issue labels (type, area), milestones (Fall MVP — 20 December, Spring AI, Evaluation), protection on `main` (changes only through pull requests with a passing CI run).
- **Literature:** search plan with nine themes linked to the research questions; nine searches logged; five sources collected with full text in the reference manager.
- **Advisor meetings:** weekly on Fridays at 10:00 (Teams) from 23 October.

Before this week (18 October): repository structure, backend skeleton with health endpoint (#1, PR #3) and backend CI workflow (#5, PR #6).

## Demonstrable output
- `docker compose up -d` starts the database; `/health/ready` reports `{"status":"ok","database":"ok"}`, and 503 once the database is stopped.
- Every pull request runs lint, format check and tests, including the database tests.
- Documents: `docs/decisions/0001-pilot-scope.md`, `docs/decisions/0002-architecture.md`, `docs/requirements.md`, `docs/ROADMAP.md`.

## Literature found so far
- Chen, Fan, Jin, Ma (2026), *Detecting Contradictions Within and Across Documents*, PACMMOD — closest related work: a hybrid of graph rules, ML and NLP for contradiction detection within and across documents (average F1 0.900). The report must state how this project differs.
- Selch et al. (2025), PRISMM-Bench (preprint) — 21 multimodal models detect document inconsistencies with 27.8–53.9% accuracy; supports using an LLM-only baseline.
- Christen (2006), *A Comparison of Personal Name Matching* — basis for the name-consistency rule.
- Ding et al. (2026), survey of MLLM-based visually rich document understanding; Ji et al. (2023), survey of hallucination; Gao et al. (2024), survey of retrieval-augmented generation.

## Problems encountered
- Port 5432 was already in use on the development machine; the local database now uses host port 5433 (configurable).
- The Netherlands checklist does not state a translation requirement; the "missing translation / certification" error type still needs an official basis.
- No study specific to Turkish-character name matching was found; the rule will rely on general name-matching literature.

## Questions for the advisor
1. Are the success criteria in `docs/requirements.md` (section 6) appropriate for fall and spring?
2. Which deadlines apply for the fall report and presentations (Lecture 2: report in week 11, presentations in week 12; course catalogue: progress presentations in weeks 13–15, proposal presentation in weeks 16–17)?
3. Is the planned evaluation (hybrid vs LLM-only, plus a small human-review comparison) sufficient for the research component?

## Goals for next week (week 6, 26 October – 1 November)
- Official source inventory with the rules each source supports (`docs/sources.md`); search for an official basis of the translation requirement.
- Source snapshot script and first snapshots (needed later for research question 3).
- Rule schema and first requirements file for the pilot, with a source for every rule.
- Data model diagram and low-fidelity screen sketches.
- Read and take notes on five papers, starting with Chen et al. (2026).
