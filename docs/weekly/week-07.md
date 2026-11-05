# Week 7 — 2026-11-02 to 2026-11-08

Fall semester week 7. Prepared for the advisor meeting on Friday, 6 November 2026 (the meeting of
30 October did not take place). Four pull requests were merged (#42, #43, #46, #48).

## Completed this week
- **Database models and migrations:** six tables for official sources, requirement sets, document
  types and their fields, checklist items and rules; first Alembic migration. Document types and
  fields are versioned with the requirement set, a change from the data model, noted in
  `docs/design/data-model.md` (#44, PR #43).
- **Seed command:** `python -m app.requirements.seed` loads the requirement files as a requirement
  set identified by the SHA-256 of its files (17 checklist items, 24 rules). Loading unchanged files
  again changes nothing; changed files give a new set that becomes the only active one, and older
  sets are kept so earlier checks stay explainable (#44, PR #43).
- **Checklist API:** `GET /checklist?destination=NL&profile=employed&lang=tr` returns the documents
  and rules for a destination and profile, each with the official source, its link and the passage
  it relies on; Turkish and English titles; Norway reports the translation requirement; 404 for an
  unknown destination and 503 without a loaded set, both documented in the API description
  (#44, PR #43; #45, PR #46).
- **Weekly source snapshot (5 November):** three of five pages had a new hash; on inspection two
  had no visible change and one a minor change (a letter-of-authorisation link on the Netherlands
  application page), recorded in `docs/sources.md`, section 6 (PR #42).
- **Related work:** four more papers read (Gao et al. 2023, ALCE; Kim et al. 2022, Donut;
  Bulatov et al. 2022; Adar et al. 2009), nine in total; `docs/related-work.md` v0.3 and
  `report/references.bib` updated (#47, PR #48).

## Demonstrable output
- `uv run alembic upgrade head` and `uv run python -m app.requirements.seed` set up the database;
  a second seed run reports "already loaded".
- `http://127.0.0.1:8000/docs` → `GET /checklist`: Netherlands employed 12 documents and 16 rules,
  student 9 and 11; Norway employed 12 and 15 with translation into English or Norwegian required.
- `RUN_INTEGRATION=1 uv run pytest`: 44 tests pass (27 before this week), locally and in CI.

## Literature read
- Bulatov et al. (2022): identity-document framework with cross-field rules and completeness
  checks, configured by hand; no new controlled experiment. **Validation after extraction is
  therefore not new either.**
- Gao et al. (2023), ALCE: measures whether cited passages support each sentence; even GPT-4
  reaches citation recall 48.5 % and precision 53.4 % (ELI5). It does not check whether a source is
  official, current or the right version.
- Kim et al. (2022), Donut: OCR-free extraction and the SynthDoG generator; not better than
  OCR-based models on every task (DocVQA 67.5 vs 78.1); no Turkish experiment.
- Adar et al. (2009): 11.5 % of about 55,000 pages differed between two simultaneous requests; a
  changed hash is only a candidate change.

**Contribution claim (unchanged in substance, narrower in wording):** requirements from official,
dated and versioned sources with the passage cited; checks on fields of visual documents;
missing-document checks across a multi-document application; an approved source change reaching
only the affected applications.

## Problems encountered
- The first CI run of PR #43 failed because Alembic was not a declared dependency; fixed, and tests
  are now always run locally with the database before a pull request.
- Inserts had to be written in dependency order (set, document types, fields, items).
- Shanthi et al. (2025) and Kazamel et al. (2025) need a subscription; Bulatov et al. (2022) was read
  instead of Shanthi, Kazamel is pending library access.

## Questions for the advisor
1. Week 8 is a buffer week: report chapters, or an early start on week 9 (authentication,
   application files, encrypted upload)?
2. How deep should the related-work chapter be: selective reading of 9–10 papers with a search
   log, or a systematic review?
3. Document types are versioned with the requirement set (a change from the data model) —
   acceptable?
4. Any route to subscription papers besides the university library?

## Goals for next week (week 8, 9 – 15 November)
- Report chapter 2 (related work) first draft, 2–3 pages; chapter 4 (design): architecture, data
  model, checklist API.
- Kazamel et al. (2025) full text and a tenth paper.
- Weekly source snapshot (9 November).
- Short ADR on the authentication method, preparing week 9.
