# Roadmap

Based on the approved CMPE 491 proposal form (work packages WP1–WP10) and the course calendar.
Fall week 1 started on 21 September 2026. Spring dates are added once the semester calendar is
known. Dates are planning targets, not course deadlines; course dates may still change and are
updated here when announced.

## Fall 2026 (CMPE 491): working prototype

| Weeks | Dates | Work | Done when |
| --- | --- | --- | --- |
| W5–W6 | 19 Oct – 1 Nov | WP1–2: requirements, pilot scope (ADR 0001), architecture (ADR 0002), PostgreSQL, official source inventory for both national layers (ADR 0001 amendment), rule schema, data model, wireframes, source snapshots start; related work and similar projects survey; LLM model and cost plan (ADR 0003) | Every rule in the requirements file cites its source |
| W7 | 2 – 8 Nov | WP3 (1/2): database models, migrations, seed, checklist API | Checklist for both profiles returned with source citations |
| W8 | 9 – 15 Nov | Buffer, report chapters | Backlog clear |
| W9 | 16 – 22 Nov | WP3 (2/2): authentication, application files, encrypted document upload, deletion | Login → application → upload → delete covered by tests |
| W10 | 23 – 29 Nov | WP4 (1/2): web client with Turkish and English interface (NFR-10), discovery page, profile wizard, personalised checklist | Checklist visible in the browser with sources, in both languages |
| W11 | 30 Nov – 6 Dec | WP4 (2/2): application dashboard, steps, upload UI, consent | End-to-end upload flow works on a phone |
| W12 | 7 – 13 Dec | WP5 (1/2): field entry, rule engine v0 | Rules produce the expected findings on a synthetic file |
| W13 | 14 – 20 Dec | WP5 (2/2): evidence-linked findings, demo data, one-command setup | Fall prototype demo |
| W14–W17 | 21 Dec – 17 Jan | Presentation, usability check, report, `v0.1.0`, exams | Report submitted, release published |

## Spring 2027 (CMPE 492): AI layer and evaluation

| Weeks | Work |
| --- | --- |
| B1 | Job queue (Celery + Redis) and WebSocket job updates |
| B2–B3 | WP8 (1/2): synthetic dataset generator, labels, frozen test set |
| B4–B6 | WP6: document classification, OCR/VLM field extraction, cross-document checks, masking |
| B7 | WP8 (2/2): LLM-only baseline and evaluation harness (AS1) |
| B8 | Buffer |
| B9–B10 | WP7: source-grounded assistant (RAG) and source change monitoring with admin approval (AS3) |
| B10–B11 | Human evaluation (AS2); final experiments on the test set; report |
| B12 | WP9: integration, end-to-end tests, usability, Nginx, PWA |
| B13 | WP10: documentation, poster |
| B14–B15 | Final presentation, `v1.0.0` |

If time runs short, the proposal's priority order applies: simplify source monitoring first,
then the assistant; the document pre-check and the experiments are kept.
