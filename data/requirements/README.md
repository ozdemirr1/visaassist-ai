# Requirement data

The checklist and the rule engine read their content from these files; nothing about a
destination's requirements is hard-coded. Schema and validation: `backend/app/requirements/`.

| File | Content |
| --- | --- |
| `document-types.yaml` | Document types and the fields the applicant enters or confirms (FR-08) |
| `eu-tr.yaml` | EU baseline for applicants in Türkiye, shared by every destination |
| `nl.yaml` | National layer: the Netherlands (main pilot destination) |
| `no.yaml` | National layer: Norway (translation requirement, ADR 0001 amendment) |

A destination's rule set is `eu-tr.yaml` plus its national file.

## Concepts
- **Requirement** — a checklist item: one document, for which profiles (`employed`, `student`),
  submitted as `original`, `copy` or `original_and_copy`. A missing required document is a finding.
- **Rule** — a check on the entered fields, with a severity (`error` or `warning`) and a `check`
  of one of these kinds:

| Kind | Checks |
| --- | --- |
| `max_age` | a date field is not older than N months/years at the application date |
| `valid_after_trip` | a date (passport expiry) is at least N months after the trip ends |
| `min_value` | an integer field is at least a value (blank pages) |
| `min_amount` | a money field is at least an amount in a currency |
| `field_true` | yes/no fields are confirmed (QR code readable, insurance territory) |
| `fields_present` | the listed fields are filled in (employer letter contents) |
| `period_covers_trip` | a period (leave, insurance) covers the whole trip |
| `covers_recent_months` | a period (bank statement) covers the last N months |
| `recent_monthly_count` | one document per month for the last N months (payslips) |
| `names_match` / `values_match` | fields on other documents equal a reference field (passport) |
| `translation_present` | every document not in the listed languages has a translation into one |

- **Citation** — every requirement and rule has `source`: the source ID from
  `data/sources.yaml`, the section and a paraphrased passage. `basis: derived` marks a rule that
  follows from the source without being stated word for word; the passage says how.

## Adding or changing a rule
1. Find the passage in the official source and add the source to `data/sources.yaml` if it is new.
2. Add the rule to the layer the source belongs to; its ID starts with the layer prefix
   (`eu-`, `nl-`, `no-`).
3. Run `uv run pytest` in `backend/`: loading fails with a list of problems if a source, document,
   field or field type does not match, or if a rule reads a document no checklist item asks for.
