# Week 6 — 2026-10-26 to 2026-11-01

Fall semester week 6. Prepared for the advisor meeting on Friday, 30 October 2026. Work started
on 23 October, right after the previous meeting; 12 pull requests were merged (#16–#38).

## Completed this week
- **Outcomes of the 23 October meeting applied:** success criteria rewritten as comparisons;
  Turkish and English interface (NFR-10); Norway added as a second national layer for the
  translation requirement (ADR 0001 amendment); advisor invited to the repository (#15, PR #16).
- **Official source inventory and snapshots:** five official sources (EU list C(2021) 5156,
  Netherlands checklist and application page, Norway checklist and visitor's visa page) in
  `data/sources.yaml` and `docs/sources.md`; snapshot command that stores a new version when
  content changes and logs every attempt; first snapshots of all five sources (#17, PR #18;
  #19, PR #20).
- **Requirement and rule files:** 13 document types, EU baseline and Netherlands/Norway layers in
  `data/requirements/`; every checklist item and rule cites its source passage; loading fails with
  a list of problems on unknown sources, fields, field types or rules that could never run;
  12 tests (#23, PR #24).
- **Positioning:** seven differences from a general chat assistant, each linked to a requirement
  and a measurement (`docs/positioning.md`, #21, PR #22).
- **Data model:** ER diagram with 19 tables (15 in fall), requirement sets versioned so every
  finding can be explained later (`docs/design/data-model.md`, #25, PR #26).
- **LLM models and cost:** model per task, four-layer credit control within USD 20 per month,
  cost estimates to be checked on the first 20 documents (ADR 0003, #27, PR #28).
- **Related work and similar projects:** 14 papers with links, seven open-source projects with
  licences and ideas to adopt, reuse policy (`docs/related-work.md`, #29, PR #30); five papers
  read and the file updated (#37, PR #38).
- **Feature ideas:** consulate e-mail drafts sent from the applicant's own mailbox and eleven
  further ideas with effort and target week (`docs/feature-ideas.md`, #31, PR #32).
- **User interface design:** five web and four mobile screens of the responsive web app
  (`docs/design/ui-design.md`, #33, PR #34).
- **Report skeleton:** LaTeX report with Chicago author-date references, nine chapters and
  appendices, 28 pages; built locally with latexmk and Biber (`report/`, #35, PR #36).

## Demonstrable output
- `uv run python -m app.sources.snapshot` captures the five official sources; unchanged pages are
  logged without a new file.
- `uv run pytest`: 25 tests pass (2 database tests run in CI); a requirement file with a wrong
  source or field type fails the build.
- Checklists from the rule files: Netherlands employed 12 documents and 16 rules, student
  9 documents; Norway adds the translation and six-month document-age rules.
- `cd report && latexmk -pdf main.tex` produces the report PDF.

## Literature read
- Chen et al. (2026), DocChecker (PACMMOD): contradiction detection within and across documents
  with LLM-assisted learned rules and external knowledge graphs; average F1 about 0.90 on 15 text
  benchmarks. A hybrid rule + ML design is therefore not new.
- Selch et al. (2026), PRISMM-Bench (ICLR 2026): 21 multimodal models reach 27.8–53.9 % accuracy
  (not F1) on 384 inconsistencies; supports an LLM-only baseline in AS1.
- Mallawaarachchi et al. (2020), web change detection survey (ACM CSUR): no shared benchmark;
  AS3 is measured on our own labelled page versions.
- Christen (2006), personal name matching: no single best technique; thresholds for the name rule
  will be chosen on local labelled pairs.
- Ding et al. (2026), MLLM document understanding survey: field extraction and rule checking are
  evaluated separately.

**Resulting contribution claim:** requirements from official, dated and versioned sources with the
passage cited; checks on fields of visual documents; missing-document checks; an approved source
change reaching only the affected applications.

## Problems encountered
- The Norwegian Directorate of Immigration's copy of the EU list rejects automated requests
  (HTTP 403); the Czech Ministry of Foreign Affairs' official copy is used instead.
- The Norway checklist carries no date inside the document; versions are identified by snapshot
  hash and retrieval date.
- The three-month payslip requirement comes from the EU list, not the Netherlands page; the rule
  cites the EU source.
- Overleaf's free plan timed out compiling the report; the report is built locally instead.

## Questions for the advisor
1. Is the contribution claim above appropriate after the DocChecker comparison?
2. Retention period for uploaded documents: 30 days after the end of the trip, or earlier on request?
3. Which feature ideas should become requirements (fall: appointment-date warnings, Norway
   translation list, name normalisation, application pack PDF)?
4. Consulate e-mails sent from the applicant's own mailbox (copy or mailto) rather than a project
   address — agreed?

## Goals for next week (week 7, 2 – 8 November)
- Database models and migrations following the data model (SQLAlchemy, Alembic).
- Seed command loading the rule files as a versioned requirement set.
- `GET /checklist?destination=NL&profile=employed` with source citations, for both profiles, with tests.
- Weekly snapshot run (2 November).
- Read five more papers; first draft paragraphs of report chapter 2.
