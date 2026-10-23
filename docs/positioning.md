# What VisaAssist AI Adds Beyond a General Chat Assistant

Version 0.1 · 2026-10-23 · Living document; examples are added as features are built.

The advisor's question (meeting of 23 October 2026): an applicant can already ask ChatGPT or
Claude which documents a Schengen visa needs, so what does this project add? This document
answers it feature by feature, states what a general assistant already does well, and links each
claim to a measurement, so the answer is shown with results rather than argued.

"General assistant" below means a general-purpose chat assistant used the usual way: the
applicant asks in a conversation, possibly with web search, without a project-specific data
model. Such assistants also change over time; the comparison is made with the versions available
when the experiments run, and the versions are reported.

## 1. What a general assistant already does well
Being honest about this keeps the comparison fair:
- Explaining visa types and the application process in plain language.
- Finding and summarising official pages when web search is available, often with links.
- Answering follow-up questions and translating terminology.

VisaAssist AI does not try to compete on conversation. It adds the parts below, which need
state, rules and data that a conversation does not keep.

## 2. Differences

### 2.1 Notifying affected applicants when an official requirement changes
**Example.** An applicant prepares a Netherlands application in November. In December the
Netherlands checklist raises a requirement, for example the bank statement period. VisaAssist AI:

1. detects the change in the weekly snapshot of the official page (`docs/sources.md`);
2. shows the administrator what changed, with the old and new passage;
3. after approval, updates the rule, which keeps a link to the new source version;
4. finds the application files that the changed rule affects, here only Netherlands files whose
   bank statements no longer meet the new period, and not Norway files or files already submitted;
5. notifies those applicants by e-mail and in the application, naming the document to replace (FR-17).

**General assistant.** It answers when asked. It does not know that the applicant has a file in
progress, which documents are in it, or that a source changed after the conversation ended. The
applicant would have to think of asking again, and the new answer would not say what changed
compared with the earlier one.

**Requirements:** FR-16, FR-17 · **Measured by:** AS3 (meaningful vs cosmetic change detection),
end-to-end test of the notification on a synthetic change.

### 2.2 Every requirement is tied to a source passage and a source version
Each checklist item and rule cites the source ID, the passage and the snapshot it was taken from
(`data/sources.yaml`, rule file). Two applicants with the same profile get the same checklist;
a later change is visible as a new version, not as a different answer.

**General assistant.** Answers can vary between runs and wordings; links, when given, point to a
page but not to the version or passage the answer relied on, and the answer may mix in
unofficial agency pages.

**Requirements:** FR-02, FR-10, NFR-03 · **Measured by:** fall criterion "generated checklist vs
checklist compiled by hand from the official sources", and the comparison with a chat
assistant's answer (missing items, wrong items, missing citations).

### 2.3 Destination-specific rules instead of a "Schengen average"
The EU baseline is the same for all Schengen states in Türkiye, but the national layers differ
(`docs/sources.md`, section 3): Norway requires every document in English or Norwegian and no
document older than six months; the Netherlands states neither. VisaAssist AI applies only the
rules of the chosen destination.

**General assistant.** Tends to give a generic Schengen list, so a Norway applicant may miss the
translation requirement or a Netherlands applicant may pay for translations that are not asked for.

**Requirements:** FR-02, FR-09 · **Measured by:** the checklist comparison above, run for both
destinations.

### 2.4 Checking the applicant's own documents against each other
The rule engine compares fields across documents: the name on the passport and on the insurance,
the insurance period against the travel dates, the leave period in the employer letter against
the trip, the age of bank statements and payslips, passport validity after the return date.
Every finding names the rule, the documents and fields involved and the source.

**General assistant.** Can read uploaded documents in one conversation, but without a fixed rule
set it is not guaranteed to run every check on every file, and its result cannot be repeated
or tested.

**Requirements:** FR-08, FR-09, FR-10, FR-14 · **Measured by:** AS1, hybrid system vs LLM-only on
the labelled synthetic test set (precision, recall, F1, false alarms, time and cost per file);
AS2, comparison with human reviewers.

### 2.5 Measured error rates instead of a confident tone
VisaAssist AI is evaluated on labelled synthetic files with injected errors, so its accuracy per
error type is known and reported, including where it fails.

**General assistant.** Its answers sound equally confident whether right or wrong; the applicant
has no error rate to judge them by.

**Requirements:** FR-22, H5 · **Measured by:** AS1 and AS2 results.

### 2.6 Application state over weeks, not one conversation
The application file keeps the profile, travel dates, uploaded documents, findings and the steps
from appointment to result (FR-06). Deadlines that follow from the data, such as a bank statement
that will be older than allowed on the appointment date, can be flagged before they become a
problem.

**General assistant.** Keeps context within a conversation and, depending on the product, some
memory across conversations, but no structured file whose fields rules can be run against.

**Requirements:** FR-05, FR-06 · **Measured by:** usability check at the end of fall.

### 2.7 Privacy by design for personal documents
Documents are encrypted at rest, kept for a limited period and deleted on request; personal
fields that a check does not need are masked before any external AI call (NFR-01, KVKK).

**General assistant.** Uploading a passport, bank statements and SGK records to a general chat
service sends all fields to that service under its own retention terms.

**Requirements:** NFR-01, NFR-02.

## 3. Summary for the report

| Difference | Section | Evidence |
| --- | --- | --- |
| Notifies affected applicants after an approved source change | 2.1 | AS3, notification test |
| Requirements tied to source passage and version | 2.2 | Checklist comparisons (fall) |
| Destination-specific rules | 2.3 | Checklist comparison, NL and NO |
| Cross-document checks on the applicant's files | 2.4 | AS1, AS2 |
| Known error rates per error type | 2.5 | AS1, AS2 |
| Application state and deadlines over time | 2.6 | Usability check |
| Masking and retention of personal data | 2.7 | NFR-01 review |
