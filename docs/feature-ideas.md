# Feature Ideas

Version 0.1 · 2026-10-23 · Proposals, not yet in the requirements

Ideas from the advisor meeting of 23 October 2026 and from the similar-projects survey
(`docs/related-work.md`). An idea becomes a requirement (FR/NFR) only after the advisor agrees
and it is planned in a week; until then it does not change the scope or the success criteria.
Each idea notes which difference from a general assistant it strengthens (`docs/positioning.md`).

Effort: **S** about one day, **M** two to four days, **L** a week or more (at about 15 hours a week).

## 1. Consulate e-mail drafts (advisor's idea)
Applicants sometimes need to write to the consulate or the service provider: asking about a
document, sending a missing document, asking about the status, rescheduling. VisaAssist AI
fills a draft from the application file.

- **What it does:** the applicant picks a purpose (question about a requirement, late or missing
  document, status enquiry, appointment change); the system fills a template in English (and
  Turkish for checking) with the application data the purpose needs (name, passport number,
  application reference, dates) and, for a requirement question, the exact source passage with
  its link. The applicant reviews it and sends it **from their own mailbox** (copy button or
  `mailto:` link).
- **Why not send from a project address** (e.g. a shared VisaAssist mailbox):
  - the consulate replies to the sender, so answers about a personal application would arrive in
    a project mailbox and the project would hold more personal data (NFR-01, KVKK);
  - messages about an application are expected from the applicant; a third-party sender can be
    ignored or treated as an agent;
  - bulk mail from one address risks being marked as spam, which would hurt every user;
  - the proposal excludes acting on the applicant's behalf with the authorities.

  If sending is wanted later, the safe form is the applicant's own account (OAuth with their
  mail provider), which is a separate decision.
- **Where it fits:** a template per purpose and destination in `data/`, filled only from
  confirmed fields; whether a destination accepts e-mail at all and to which address is
  recorded from the official contact page in `docs/sources.md`.
- **Strengthens:** 2.6 (application state), 2.2 (cited passages) · **Effort:** M · **When:** fall W13
  or spring.

## 2. From the similar-projects survey

| Idea | Seen in | What it adds | Effort | When |
| --- | --- | --- | --- | --- |
| Prompt-injection scan of uploaded documents before any LLM call | VISAPATH | A document with hidden instructions cannot steer extraction or the assistant; security point for the report | S | spring B4 |
| Read the passport's machine-readable zone (MRZ) | UK Visa Auditor | Name, passport number, birth and expiry dates from a checksummed line: exact, free, and a reference for the name rule | M | spring B4 (fall: optional) |
| Blocking checks: an application cannot be marked ready while an error finding is open | Visa-Agent | Makes the rule engine's result visible in the flow | S | fall W12 |
| Export an application pack (checklist, findings, documents in checklist order, PDF) | Visa-Agent | The applicant takes a clean, ordered pack to the appointment | M | fall W13 |
| Hybrid retrieval: pgvector + PostgreSQL full-text, merged with reciprocal rank fusion | visa-assistant | Better retrieval of exact terms such as "SGK" or "YÖK" that embeddings miss | S | spring B9 |
| Ignore rules for page parts (menus, scripts) before comparing snapshots | changedetection.io | Fewer cosmetic changes reach the administrator; baseline for AS3 | S | spring B10 |

## 3. Further ideas

| Idea | What it adds | Strengthens | Effort | When |
| --- | --- | --- | --- | --- |
| Deadline warnings: "this bank statement will be older than allowed on your appointment date" | Rules evaluated at the appointment date, not only today | 2.6 | S | fall W12 |
| Translation list for Norway: which uploaded documents still need an English or Norwegian translation | Turns the translation rule into a to-do list | 2.3 | S | fall W12 |
| "What changed since your last visit" on the application page | Shows approved source changes affecting the file, with old and new passage | 2.1 | S | spring B10 |
| Name normalisation (Turkish characters, letter case, order of given names) before matching, with the rule explaining what was normalised | Fewer false name-mismatch findings | 2.4 | S | fall W12 |
| Destination comparison: the same profile's checklist for the Netherlands and Norway side by side | Shows national differences directly | 2.3 | S | fall W10 |

## 4. Not planned
- Booking or watching appointment slots, submitting applications: excluded by the proposal.
- Predicting the visa decision: excluded by the proposal (NFR-03).
