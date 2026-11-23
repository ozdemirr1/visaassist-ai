# 0007 — A model in the fall prototype
Date: 2026-11-20 · Status: Accepted (agreed with the advisor on 20 November 2026)

## Context
ADR 0003 placed every model call in the spring; the fall prototype checks fields that the
applicant enters. At the meeting of 20 November 2026 the advisor asked for the prototype to work
with a model before the CMPE 491 presentation: a prototype of this proposal without one would show
a website, not the approach. He left the model choice open, suggested a strong hosted model (Claude
or GPT) for the fall, and the move to the cheapest adequate model in spring, preferably an open
model on the project's own server or a server in Türkiye, because sending real personal data to a
provider abroad may conflict with the Turkish data-protection law (KVKK). He also suggested giving
the same model the same task without the system, so that the two can be compared.

The developer's machine (MacBook Air M2, 8 GB) cannot run a vision-language model next to Docker
and a browser at a usable speed, so a local model is not an option for the fall demo.

## Decision
1. **Task:** field extraction (FR-13). For an uploaded document the model returns the fields its
   document type defines. The values are validated against the field types, shown to the
   applicant, and stored only after the applicant confirms or corrects them. The rule engine
   decides as before; no finding rests on the model alone.
2. **Provider:** OpenAI, through one client module with a provider-neutral interface, so an open
   model can replace it without changes elsewhere. A cheaper model (for example `gpt-5.4-mini`) is
   used in development, a stronger one (for example `gpt-5.4`) for the measurement and the
   presentation; the exact models are fixed after a first trial and reported with their dates.
3. **Data:** in the fall only synthetic documents marked SAMPLE, rendered from `data/demo/`, are
   sent to the model. No real personal document is sent. The API key is kept only in `.env`.
4. **Cost:** at most USD 20 per month (NFR-06): a hard limit in the provider account, the token
   count and cost of every call logged, results cached per document, and no real model call in the
   automated tests (the model is replaced by a fake). Estimate with the list prices of November
   2026 and about 2,500 input and 1,500 output tokens per document: USD 15–18 for development,
   three runs of the comparison and the presentation.
5. **Comparison:** the same model is run alone on the documents of each demo file and with the
   rule engine, on the clean files and on every labelled error; errors found, false alarms, time
   and cost per file are reported (report, Section 6.2).
6. **Spring:** OCR fallback, confidence per field, classification of the document type, masking
   of fields a check does not need, and a move to an open model on the project's own server or a
   Turkish server, with a KVKK review before real documents are allowed.

ADR 0006, decision 9 (the order of the remaining work) changes accordingly: the model comes
before the remaining report chapters, because the comparison is the main result of Chapter 6.

## Alternatives considered
- **No model in the fall (ADR 0003 as it was):** rejected by the advisor; the prototype would not
  show the hybrid approach.
- **A local open model now:** free and closer to the KVKK goal, but too slow and too weak on an
  8 GB laptop; planned for spring on a server.
- **The source-grounded assistant first (FR-15):** answers the "why not ChatGPT" question, but
  does not touch the document check, which is the proposal's main claim; it follows if time allows.

## Consequences
- The fall prototype reads documents; the advisor's question "does it parse the PDF?" gets a
  working answer.
- Synthetic document images are needed: the SAMPLE PDFs of the demo loader carry only text.
- The report's Chapters 4 to 6 and 8 describe the model, the data sent to it and the comparison.
- Every model call costs money; the tests must not make real calls.

## Amendment, 23 November 2026: the models
After FR-13 was built (#110) the models were fixed from the provider's model list and price page
of 23 November 2026 (standard tier, USD per million input / output tokens):

- development and the default of the API: `gpt-6.1-terra` (1.00 / 5.00), which the provider
  describes as fast and efficient for visual reasoning;
- measurement (Section 6.2) and the presentation: `gpt-6.2-sol` (2.00 / 10.00).

`gpt-5.4-mini` and `gpt-5.4`, named above as examples, are still available and stay in the price
table. With about 2,500 input and 300 to 1,500 output tokens per document, one document costs
about USD 0.004 to 0.01 with Terra and 0.008 to 0.02 with Sol, so three runs of the comparison on
the 37 demo images stay below USD 3. The limits in force: a USD 20 prepaid credit without
automatic recharge, a USD 20 monthly hard spend limit in the provider account, a separate
provider project with its own key, and the API's own stop at USD 20 per month. Caching results
per document (point 4) is not built yet.
