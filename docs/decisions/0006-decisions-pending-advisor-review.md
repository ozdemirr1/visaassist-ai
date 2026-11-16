# 0006 — Decisions taken while advisor review is pending
Date: 2026-11-16 · Status: Accepted by the author (open to revision by the advisor)

## Context
The weekly notes of weeks 6, 7 and 8 carry twelve questions for the advisor. The meetings in
which they were to be discussed did not take place, and the work is about four weeks ahead of
the roadmap, so waiting would stop the project. Each question was written with a proposal, and
the work has followed those proposals since. This record turns the proposals into decisions, so
that the report and the code rest on something written down, and lists what a different answer
from the advisor would cost to change.

## Decision
Every item below is decided as proposed. A different answer from the advisor replaces it; the
last column says what would then have to change.

| # | Question | Decision | If the advisor decides otherwise |
| --- | --- | --- | --- |
| 1 | Is the contribution claim (four points) correct and sufficient? | Yes: versioned, source-linked requirements; checks on fields of visual documents; missing-document and consistency checks across a multi-document file; a source change reaching only the affected applications | Report chapters 1 and 2 are reworded; no code changes |
| 2 | How long are uploaded documents kept? | 30 days after the trip ends, and at once on request (ADR 0005) | One constant (`RETENTION_AFTER_TRIP`) and the consent text |
| 3 | Which extra features become requirements? | Done in fall: translation requirement for Norway, name normalisation, days to the appointment. Kept for after the report: application package as one PDF, a warning when the application date is outside the allowed window. Spring: prompt-injection screening of uploads, reading the passport's machine-readable zone | Reordering of the backlog |
| 4 | From whose address are e-mails to a consulate sent? | From the applicant's own (a prepared text to copy); the system sends nothing on the applicant's behalf | None built yet |
| 5 | Buffer week: report or the work of week 9? | Both were done; closed | — |
| 6 | How deep is the related-work chapter? | Selective reading of ten studies with a search log, two to three pages; not a systematic review | More reading time in December |
| 7 | Document types versioned with the requirement set (a change from the data model)? | Yes, kept | A migration; earlier checks would lose their catalogue |
| 8 | Papers behind a subscription (Kazamel 2025, Shanthi 2025)? | Obtain through the library until 22 November; otherwise replace each with an open-access study on the same topic and say so in the search log | One paragraph of chapter 2 |
| 9 | The work is ahead of the plan: what comes next? | The report first (the course schedule names week 11 for the report and week 12 for the presentation; the dates are not confirmed), then demo data and a one-command setup, then a usability check with three people, then an early start on the synthetic data set of spring | Reordering only |
| 10 | Is the consent text written by the student enough? | For a prototype that holds only synthetic documents, yes; it is named as a limitation in the report. No real personal document is uploaded, also not in the usability check, before the text has been reviewed for the Turkish data-protection law (KVKK) | The text is reviewed earlier; consent gets a new version and is asked again (already supported) |
| 11 | Are the assumptions of the rule engine acceptable where the sources are silent? | Yes, as long as each stays marked as an assumption in the code, the requirement files and the report: the bank statement ends at most one month before the application; the newest payslip is from the application month or the two before; amounts in another currency than the rule's are not compared; for Norway the application form, passport and photo need no translation | Constants in `app/rules/engine.py` and one line of `data/requirements/no.yaml` |
| 12 | How is progress reported in a week without a meeting? | The weekly note and the meeting document are sent by e-mail on Thursday evening; open decisions are recorded here | — |

ADR 0004 (authentication) and ADR 0005 (document storage and consent) stay in force on the same
terms: accepted by the author, open to revision.

## Alternatives considered
- **Waiting for answers:** the fall prototype and the report would slip for questions whose
  proposed answers are cheap to change later.
- **Deciding without a record:** the proposals were already being followed; without a record the
  report could not say which choices are the student's own and which were confirmed.

## Consequences
- The report can state each of these choices and name it as the author's decision.
- Nothing here is expensive to reverse: the table names the cost of every reversal.
- Two matters are not decided here because they are the repository owner's to decide: the
  licence of the code, and whether copies of official pages stay in `data/snapshots/` while the
  repository is public.
