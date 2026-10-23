# Requirements Specification

Version 0.2 · 2026-10-23 · Updated after the advisor meeting of 23 October 2026

Sources: the approved project proposal, the CMPE 491 proposal form (v1.2), ADR 0001 (pilot scope)
and ADR 0002 (architecture). Goal IDs H1–H5 refer to the proposal's objectives:
H1 personalisation, H2 document pre-check, H3 up-to-date information, H4 source-grounded
information, H5 measurable AI performance.

## 1. Purpose and scope
VisaAssist AI helps applicants in Türkiye prepare a visa application without an intermediary:
it builds a personalised checklist from official sources, checks the uploaded documents against
the requirements and against each other, and shows the evidence behind every finding.

**Pilot scope (ADR 0001):** the Netherlands, Schengen short-stay visa (type C) for tourism,
employed and student (higher education) applicants. A second Schengen destination whose official
checklist states a translation requirement is added as a further national layer, so that the
missing-translation check rests on an official source (ADR 0001, amendment of 23 October 2026).
Other destinations and profiles follow the same data model later.

**Out of scope:** predicting or guaranteeing a visa decision; legal advice; submitting
applications or booking appointments on the user's behalf; using real applicants' documents in
development, tests or experiments.

## 2. Users and stakeholders
| Role | Needs |
| --- | --- |
| Applicant (employed or student) | Know which documents are needed, upload them, see problems before applying |
| Administrator | Maintain requirements and expert notes, review detected source changes before they go live |
| Researcher (project author) | Generate labelled synthetic files, run and compare approaches, measure results |
| Advisor and course coordinator | Follow progress, agree on success criteria, assess the outcome |

## 3. Functional requirements
Priority: **Must** = required for the semester's outcome, **Should** = planned, **Could** = only if time allows.

| ID | Requirement | Goal | Priority | Semester |
| --- | --- | --- | --- | --- |
| FR-01 | The applicant selects destination, visa type, profile and travel dates. | H1 | Must | Fall |
| FR-02 | The system shows a personalised checklist; each item states whether an original, a translation or notarisation is needed and links to its official source. | H1, H4 | Must | Fall |
| FR-03 | A discovery page shows, for the destination, Schengen membership, appointment and biometrics information and official links. | H1, H4 | Should | Fall |
| FR-04 | Users register and log in; roles are applicant and administrator. | — | Must | Fall |
| FR-05 | The applicant creates, lists and deletes application files. | — | Must | Fall |
| FR-06 | The applicant tracks the application steps (appointment → documents → submission → result). | H1 | Should | Fall |
| FR-07 | The applicant uploads documents per checklist item (PDF, JPEG, PNG), including from a phone camera. | H2 | Must | Fall |
| FR-08 | The applicant enters or confirms the key fields of each document (names, dates, amounts, coverage). | H2 | Must | Fall |
| FR-09 | Rule checks detect missing documents, documents older than allowed, insufficient passport validity, insurance that does not meet the minimum or does not cover the trip, name mismatches across documents and leave periods that do not cover the trip. | H2 | Must | Fall |
| FR-10 | Every finding shows the rule, the documents and fields involved, the official source and a severity. | H2, H4 | Must | Fall |
| FR-11 | The applicant deletes uploaded documents and application files; deletion removes the stored files. | — | Must | Fall |
| FR-12 | The system classifies the type of an uploaded document. | H2 | Must | Spring |
| FR-13 | The system extracts fields with OCR and a vision-language model, stores a confidence per field and asks the applicant to confirm low-confidence fields. | H2 | Must | Spring |
| FR-14 | Cross-document checks cover all pilot document pairs (passport, bank statement, payslips, employer letter, SGK records, YÖK certificate, insurance, travel and accommodation bookings). | H2 | Must | Spring |
| FR-15 | An assistant answers questions from official sources and expert notes, cites the passages it used and does not give a definitive answer without a source. | H4 | Must | Spring |
| FR-16 | Official pages are captured periodically; changes are detected, summarised, linked to the requirements they may affect and sent to an administrator. No change goes live without approval. | H3 | Must | Spring |
| FR-17 | After an approved change, affected applicants are notified by e-mail and in the application. | H3 | Should | Spring |
| FR-18 | Administrators manage requirements and expert notes in the web application. | H3, H4 | Should | Spring |
| FR-19 | Long-running checks report their status to the browser while they run. | — | Should | Spring |
| FR-20 | The web application can be installed on a phone (PWA). | — | Could | Spring |
| FR-21 | Applicants can message an expert. | — | Could | Spring |
| FR-22 | Research tooling generates labelled synthetic application files, runs an LLM-only baseline and computes the evaluation metrics. | H5 | Must | Spring |

## 4. Non-functional requirements
| ID | Requirement |
| --- | --- |
| NFR-01 Privacy (KVKK) | Explicit consent before the first upload; documents encrypted at rest; a limited retention period; deletion on request; personal fields not needed for a check are masked before any external AI call; no real personal documents in development, tests or experiments. |
| NFR-02 Security | Passwords stored as salted hashes; token-based authentication; applicants can access only their own files; secrets only in `.env`; the database is not exposed to the network. |
| NFR-03 Transparency | Every requirement, finding and assistant answer links to its source; every result page states that the system prepares and does not predict or guarantee a decision. |
| NFR-04 Usability | Responsive interface usable on a 375 px wide phone screen and on desktop; upload status and findings understandable without technical knowledge. |
| NFR-05 Performance | Fall rule checks return within 2 seconds for one application file on the development machine; spring extraction time per document is measured and reported. |
| NFR-06 Cost | OpenAI usage stays within USD 20 per month; the cost of every evaluation run is logged. |
| NFR-07 Reproducibility | The system starts with Docker Compose following the README; dependencies are pinned (`uv.lock`); CI runs lint and tests on every pull request. |
| NFR-08 Maintainability | Every rule has unit tests; decisions are recorded as ADRs; code and repository documents are in English. |
| NFR-09 Robustness | Uploads are validated for type and size (at most 10 MB per file); the API exposes liveness and readiness checks. |
| NFR-10 Languages | The applicant interface is available in Turkish and English, selectable at any time; all interface text comes from translation files, none is hard-coded. Quoted passages of official sources are shown in their original language with the link. |

## 5. Constraints and limitations
- One developer with about 15 hours per week, over two semesters.
- OpenAI budget of at most USD 20 per month.
- Evaluation uses synthetic documents only, so results may not fully transfer to real applications; this limitation is reported.
- Official pages can change without notice; the pilot relies on the sources listed in ADR 0001.
- The pilot covers one main destination (plus a second national layer for the translation
  requirement), one visa category and two profiles.

## 6. Success criteria
Agreed with the advisor on 23 October 2026: the criteria are sufficient, and every result is
stated as a comparison against a reference or an alternative, never as an isolated score.
Results are reported as measured; no score is promised in advance.

**End of fall (prototype):**
- An applicant of each pilot profile completes the flow: profile → checklist → upload → field entry → findings.
- The generated checklist is compared item by item with a checklist compiled by hand from the
  official sources (missing, extra and differing items); every item and every rule cites its source.
- On the demo application files, the rule engine's findings are compared with the injected error
  labels: every injected error of the supported types is reported, and the error-free file gets no finding.
- The checklist for a pilot profile is compared with the answer a general-purpose chat assistant
  (LLM only, no sources) gives to the same question: missing items, wrong items and missing citations.
- The system starts by following the README; all tests pass in CI.

**End of spring (complete project):**
- A labelled synthetic dataset (target: about 200 files, 1,000+ documents) with a frozen test set.
- Hybrid and LLM-only approaches compared per error type on the test set with precision, recall,
  F1, false-alarm rate, time and cost per file (AS1).
- Human reviewers compared with the hybrid system on a subset of the test set: accuracy and time
  per file (AS2).
- Change detection compared with labelled page versions: meaningful versus cosmetic changes,
  precision and recall, against a plain text-diff baseline (AS3).
- Assistant answers compared with LLM-only answers to the same questions: citation coverage and
  unsupported statements.
- Final report and documentation sufficient for another engineer to re-implement the system.

## 7. Methodology (summary)
Incremental delivery in weekly increments: one end-to-end flow first, then automation. Each
increment is an issue, a pull request with tests and a green CI run. AI components are added in
the spring and evaluated against an LLM-only baseline and human reviewers on synthetic data
with injected, labelled errors, keeping development and test data separate.

## 8. Open questions
- Which second destination provides the official translation requirement (week 6 source
  inventory; candidates in ADR 0001).

Resolved on 23 October 2026: interface language (Turkish and English, NFR-10); basis for the
translation requirement (a second destination, ADR 0001); success criteria (section 6).
