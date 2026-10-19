# 0001 — Pilot scope: Netherlands, Schengen short-stay tourism, employed and student applicants
Date: 2026-10-19 · Status: Accepted

## Context
The approved CMPE 491 proposal form limits the initial pilot to one destination and one
short-stay visa category, with student and employed applicant profiles. The pilot needs a
destination whose official requirements for applicants in Türkiye are complete, public,
stable enough to model as rules, and versioned so that changes can be detected later (AS3).

## Decision
- **Destination:** the Netherlands.
- **Visa category:** Schengen short-stay visa (type C), purpose *tourism*.
- **Profiles:** employed applicant; student applicant (higher education).
- **Requirement sources, in two layers:**
  1. EU baseline: the harmonised list of supporting documents for short-stay visa applicants
     in Türkiye, Commission Implementing Decision C(2021) 5156 (29 July 2021).
  2. National layer: the Netherlands Worldwide checklist "Schengen visa – tourism – Türkiye"
     (published 20 August 2025, last modified 28 August 2025 at the time of review).
- Every rule in the system cites the source and the passage it comes from.

Requirements taken from these sources that the rule engine can check directly:
passport issued within the last 10 years and valid at least 3 months after leaving the
Schengen area; photo not older than 6 months; bank statements covering the last 3 months;
3 recent payslips (employed); employer letter with specified contents and SGK documents with a
readable QR code (employed); YÖK student certificate with a readable QR code (student);
travel medical insurance in the applicant's name covering all Schengen states and the whole
stay with at least EUR 30,000.

## Alternatives considered
- **Germany:** largest demand, but an official, complete checklist for applicants in Türkiye
  could not be located easily; search results were dominated by agency pages.
- **Norway:** detailed all-category checklist including a translation rule and a general
  "no document older than 6 months" rule, but a single PDF without a version date.
- **Switzerland:** dated per-purpose PDFs, but in German/French, which makes the pilot sources
  harder to work with.

## Consequences
- Both pilot profiles are described with concrete, checkable documents, which supports the
  cross-document checks (names, dates, insurance coverage, leave period).
- The Netherlands page shows publication and modification dates, which helps source
  monitoring and AS3 labelling.
- The EU baseline is shared by all Schengen states in Türkiye, so a second destination later
  only adds a national layer.
- Open gap: the Netherlands checklist does not state a translation requirement. The
  "missing translation / certification" error type needs an official basis; if none is
  found, that error type is excluded from the pilot and the exclusion is documented.
