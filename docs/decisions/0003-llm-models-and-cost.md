# 0003 — LLM models and API cost control
Date: 2026-10-23 · Status: Accepted

## Context
The advisor asked which LLM the project uses and how the API credit will be managed (meeting of
23 October 2026). The proposal fixes OpenAI as the provider and a budget of at most USD 20 per
month (NFR-06). The fall prototype has no AI component (fields are entered by the applicant);
the models are needed in spring for document classification and field extraction (FR-12,
FR-13), the source-grounded assistant (FR-15), change summaries (FR-16) and the LLM-only
baseline of the evaluation (AS1).

Prices below are from the official OpenAI pricing page on 23 October 2026, per 1M tokens,
standard tier. They change often; the price table in the configuration is updated with them.

| Model | Input | Cached input | Output | Batch / Flex (input / output) |
| --- | --- | --- | --- | --- |
| gpt-6-luna | $0.10 | $0.01 | $0.50 | $0.05 / $0.25 |
| gpt-6.1-sol | $2.00 | $0.10 | $10.00 | $1.00 / $5.00 |
| gpt-6-astra | $10.00 | $1.00 | $50.00 | $5.00 / $25.00 |
| text-embedding-3-small | $0.02 | — | — | — |

GPT-6 Luna accepts text and image input with a 272k-token context window.

## Decision
1. **One provider, models chosen per task and set in configuration.** All calls go through one
   small client module; the model of each task is an environment variable, so a model can be
   replaced without code changes.

   | Task | Model | Why |
   | --- | --- | --- |
   | Document classification and field extraction (FR-12, FR-13) | gpt-6-luna | image input, structured output, lowest cost; high volume |
   | Second pass for low-confidence fields | gpt-6.1-sol | only for fields the first pass marks uncertain |
   | Assistant answers (FR-15) and change summaries (FR-16) | gpt-6-luna | short answers from retrieved passages |
   | Embeddings for retrieval (FR-15) | text-embedding-3-small | pgvector, low cost |
   | LLM-only baseline (AS1) | gpt-6-luna **and** gpt-6.1-sol | the comparison is reported against a cheap and a strong model, so the result does not depend on a weak baseline |
   | Fall checklist comparison with a general assistant | gpt-6.1-sol | a handful of calls |

   gpt-6-astra is not used: at five times the price of gpt-6.1-sol it would take most of the
   monthly budget for one evaluation run.

2. **Credit is managed in four layers.**
   1. *Provider limits:* a separate OpenAI project for VisaAssist AI with its own API key (only in
      `.env`); a hard monthly spend limit of USD 20 on the project; spend alerts at USD 10 and 15.
      A reached limit returns HTTP 429 `project_spend_limit_exceeded`, which the client turns
      into a clear "budget reached" error instead of a crash.
   2. *Budget guard in the application:* every call is logged with task, model, input, cached and
      output tokens and computed cost (a spring `llm_calls` table). Before each call the
      month-to-date cost is compared with `LLM_MONTHLY_BUDGET_USD` (default 18, below the hard
      limit); above it, calls are refused. Evaluation runs also have their own cap.
   3. *Fewer paid tokens:* results are cached by document hash, model and prompt version, so a
      re-run of an unchanged document costs nothing; the fixed system prompts use prompt caching;
      evaluation runs use the Batch tier (half price); masking personal fields (NFR-01) also
      shortens the input.
   4. *No paid calls in development:* tests and CI use recorded responses; only explicit commands
      (an extraction run, an evaluation run) call the API.

3. **Estimates are checked against measurement.** The figures below assume about 2,000 input
   tokens per document image with the prompt and 300 output tokens. The first 20 synthetic
   documents are run before any larger job, and this table is updated with the measured
   tokens.

   | Job | Volume | gpt-6-luna | gpt-6.1-sol |
   | --- | --- | --- | --- |
   | Extraction, whole dataset | 1,000 documents | ≈ $0.35 | ≈ $7.00 |
   | LLM-only baseline, one run | 200 files × 6 documents | ≈ $0.42 | ≈ $8.40 |
   | Same, Batch tier | | ≈ $0.21 | ≈ $4.20 |

   Three baseline runs with both models on the Batch tier stay near USD 13, which fits into one
   month; dataset extraction and the baseline are scheduled in different months.

## Alternatives considered
- **A single strong model for everything:** simpler, but extraction on the whole dataset and
  repeated baseline runs would exceed the monthly budget.
- **Only local OCR (Tesseract) without an LLM:** no cost and kept as a fallback (ADR 0002), but it
  does not classify documents or return structured fields with confidence.
- **Local open models:** no API cost, but too slow on the development laptop for a 1,000-document
  dataset and harder to reproduce for another engineer.
- **Another provider:** possible through the same client module; not chosen because the proposal
  and the budget are set for OpenAI.

## Consequences
- The data model gets an `llm_calls` table in spring (`docs/design/data-model.md`).
- The report states model names, dates and prices used, because models and prices change during
  the project; results are always reported with the model version.
- The OpenAI project, the hard limit and the alerts are set up before the first spring call (B1).
