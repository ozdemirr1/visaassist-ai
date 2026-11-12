# Week 8 — 2026-11-09 to 2026-11-15

Fall semester week 8, a buffer week in the roadmap. Prepared for the advisor meeting on Friday,
13 November 2026 (the meetings of 30 October and 6 November did not take place; the eight open
questions of weeks 6 and 7 were sent to the advisor by e-mail on 10 November). The planned
backlog was cleared early in the week and the work of weeks 9 to 12, and the findings page of week
13, was done ahead of schedule. Seventeen pull requests were merged (#52 to #84).

## Completed this week
**Planned for week 8**
- **Weekly source snapshot (10 November):** two pages of the Netherlands had a new hash, one with
  no visible change and one minor; no requirement changed (#51, PR #52). Over three weeks, five
  changed hashes: three without a visible change, two minor, none affecting a requirement.
- **Report:** first drafts of chapter 2 (related work, nine studies) and chapter 4 (system design:
  architecture, data model, rule kinds, checklist service, source monitoring, AI cost); the report
  has 34 pages (#53, PR #54; #55, PR #56).
- **ADR 0004, authentication:** e-mail and password with Argon2id, an opaque session token in an
  HttpOnly cookie, a custom header against cross-site requests, a 15-minute wait after five failed
  logins (#57, PR #58).

**Week 9, done ahead (backend)**
- **Accounts and sessions:** register, login, logout, current user (#59, PR #60).
- **Application files:** create, list, change, delete, with dated steps; visible only to their
  owner (#61, PR #62).
- **ADR 0005 and encrypted documents:** consent before the first upload; each document encrypted
  with its own AES-256-GCM key, wrapped by a master key outside the repository; stored under a
  random name; type taken from the file's first bytes (PDF, JPEG, PNG), at most 10 MB; deletion
  removes the file at once; documents expire 30 days after the trip (#63, PR #64; #65, PR #66).

**Week 10, done ahead (web client)**
- **Web client in Turkish and English:** React, TypeScript, Tailwind; checklist page with the
  official source of every item; registration and login; a test keeps both translation files
  identical in keys (#67, PR #68).
- **New-application wizard and application page** (#69, PR #70). The frontend checks are now
  required on every pull request.

**Week 11, done ahead (application page and upload)**
- **New visual design:** two examples were drawn and compared; the chosen one has a navy side
  panel (a bottom bar on phones), a route card, a readiness ring with one segment per document, a
  dated step line, a document table with search and filter, and a source panel. Motion is turned
  off for users who ask their system to reduce it. `docs/design/ui-design.md` v0.2
  (#71, PR #72; #73, PR #74).
- **Consent screen and document upload:** the consent text is shown before the first upload;
  drop zone per checklist item; list, download and two-step delete; withdrawing consent deletes
  all documents; the readiness figures follow the uploads (#75, PR #76).
- **Location data removed from photos** before storing: the GPS block of the EXIF data and the
  XMP packet in JPEG, the EXIF GPS block in PNG, without an image library (#75, PR #76).

**Weeks 12 and 13, done ahead (field entry, rule engine, findings)**
- **Field entry:** the applicant enters the key fields of each uploaded document; the values are
  encrypted with the document's own key (ADR 0005, amendment) (#79, PR #80).
- **Rule engine v0:** all twelve rule kinds of `data/requirements/` as pure functions; a rule ends
  as passed, failed, incomplete (a value is missing) or skipped (its document is not uploaded).
  Dates are compared with the trip and the application date of the file, never with the day the
  check runs. Names are compared without case, Turkish letters or order (#79, PR #80).
- **Findings page with kept checks:** missing documents, problems and passed rules in groups,
  each problem with the official passage; a kept check stores the state of the rules and where
  each issue is, not the entered values, and shows the change since the one before (#81, PR #82).
- **Destination page:** where and when to apply, fingerprints, fees and translation for the
  Netherlands and Norway, each fact with its official source, read from the snapshots of 5 and
  10 November (`data/destinations.yaml`) (#81, PR #82).
- **Report chapter 1** (introduction: problem, contributions, organisation) (#81, PR #82).
- **Tried on a phone** (iPhone, Safari), including a photo taken with the camera; three layout
  problems found and fixed; screenshots of the application as built added to
  `docs/design/ui-design.md` (#83, PR #84).

## Demonstrable output
- `docker compose up -d`, `uv run uvicorn app.main:app` and `npm run dev`: register → new
  application (Netherlands, employed) → accept the consent text → upload a PDF for "transport
  reservation" → the item turns "ready", the ring shows 1 of 12 → enter its fields → the rules
  change state → findings page → keep the result → download → delete.
- The checklist page works without an account, in Turkish and English, with the official passage
  of each document and rule.
- Tests: backend 186 (44 last week), frontend 39 (new); both run in CI on every pull request.

## Literature read
No new paper this week. Kazamel et al. (2025) is still waiting for library access; the tenth paper
is not chosen yet.

## Problems encountered
- Safari refuses `Secure` cookies on `http://localhost`, so login seemed to work and the next
  request was rejected; `COOKIE_SECURE=false` is set in the local `.env` only.
- Two authentication tests depended on the developer's machine (that `.env` setting, and real
  sessions in the development database) while passing in CI; the tests now set their own values
  and look only at their own user (PR #76).
- `npm install` failed with a certificate error caused by a half-finished OpenSSL upgrade on the
  development machine; solved by pointing Node to the system certificate file.
- The first web pages looked too plain; a redesign was done before more pages were built on them.
- The data model planned to store the compared values with each finding; that contradicts keeping
  field values encrypted, so a kept check stores rule states and issue locations only.
- On an iPhone, date fields were wider than their card, the page zoomed when a field was focused,
  and the document table hid its status column; fixed in PR #84.

## Limits of this week's work
- No AI layer yet: the applicant enters the fields by hand; extraction follows in spring.
- Assumptions of the rule engine where the sources are silent: a bank statement covers at least
  three months and ends at most one month before the application; payslips are for three months
  in a row, the newest from the application month or the two before; an insurance amount in
  another currency than EUR is not compared; for Norway the application form, the passport and the
  photo are exempt from translation (our reading, the source makes no exception).
- Demo data and a one-command setup (the rest of week 13) are not done.
- The consent text describes what the system does, but has not been reviewed for the Turkish
  data-protection law (KVKK).
- Location removal does not cover metadata inside PDF files or XMP in PNG; HEIC photos are refused.

## Questions for the advisor
1. The eight questions of weeks 6 and 7 (sent by e-mail on 10 November) are still open; the work
   follows the proposals written next to them until they are answered.
2. The work is about four weeks ahead of the plan. Proposal: first demo data and the one-command
   setup, then the report and a usability check with three applicants, then an early start on the
   synthetic data set of spring. Agreed?
3. Is a consent text written by the student enough for a prototype with synthetic documents, or
   should it be reviewed against KVKK before the demo?
4. Retention: documents are deleted 30 days after the trip ends. Is that period acceptable?
5. Are the assumptions of the rule engine listed above acceptable, if they stay marked as
   assumptions in the code and the report?
6. In weeks without a meeting, how should progress be reported? Proposal: the weekly note and the
   meeting document by e-mail on Thursday evening.

## Goals for next week (week 9, 16 – 22 November)
- Demo data: two synthetic application files marked "SAMPLE" with controlled errors.
- One-command setup with Docker Compose and the steps in the README.
- Report chapter 5 (implementation), first draft.
- Kazamel et al. (2025) full text and a tenth paper; report chapter 2 updated.
- Weekly source snapshot.
