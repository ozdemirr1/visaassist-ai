# Field extraction runs

Every run of `python -m app.demo.read_fields` that the report uses, or that changed the prompt, is
kept here: one JSON line per image and run (`ImageResult` in `backend/app/demo/read_fields.py`).
Only the synthetic SAMPLE images of `data/demo/documents/` were sent; the files hold the values the
model read from them, its token counts and the list-price cost.

A value counts as correct when the rule engine would treat it as the expected value (names without
case, Turkish letters, order or a title; document numbers without spaces; dates, numbers and amounts
exactly).

## Development runs (these images also serve the measurement, see "Threat to validity")

| File | Date | Model | Prompt | Images | Fields correct | Cost (USD, list price) |
| --- | --- | --- | --- | --- | --- | --- |
| `2026-11-23_gpt-6.1-terra_extract-v1.jsonl` | 23 Nov 2026 | `gpt-6.1-terra` | extract-v1 | 23 clean | 83 / 90 (92.2%) | 0.0864 |
| `2026-11-23_gpt-6.1-terra_extract-v2.jsonl` | 23 Nov 2026 | `gpt-6.1-terra` | extract-v2 | 23 clean | 90 / 90 (100%) | 0.0859 |

### extract-v1 → extract-v2

The seven wrong values of the first run, and what changed:

| Field | Count | What the model returned | Change |
| --- | --- | --- | --- |
| `application_form.signed`, `passport.signed` | 4 | `false`, although the signature field holds a name in a script typeface | hint: true if the field holds a signature in any style, false if empty |
| `travel_reservation.passenger_name` | 2 | `ORNEK/DENIZ MR`: the booking's title was kept | instructions: names without a title; the rule engine also ignores titles (`MR`, `MRS`, `MS`, `MISS`, `MSTR`, `DR`, `BAY`, `BAYAN`), because a real booking prints them and an applicant may type them |
| `employer_letter.employer_contact` | 1 | `null`; the letterhead gives only the company and the city | hint: the employer's name with its address, city, telephone or e-mail, usually in the letterhead |

With the title rule, `ORNEK/DENIZ MR` already matches the passport, so the rule `eu-rule-names-match`
would not have raised a false alarm; the field is still scored wrong for v1 because the scoring
of v1 did not ignore titles.

With extract-v2 the same model read all 90 values correctly, at 3.0 s per image on average. After
this change the prompt is frozen: the measurement of the report (Section 6.2) uses
extract-v2 unchanged.

## Cost: list price and the provider's bill

The cost in these files is the list price of the logged tokens (`backend/app/ai/prices.py`). The
provider's usage page showed a higher amount for the first calls (USD 0.0048 for a call logged at
0.0040, with the same token count), possibly because writing the prompt to the provider's cache is
billed above the input price. The provider's bill is the authoritative figure and is reported next
to these values once its daily totals are complete.

## Threat to validity

The prompt was adjusted on the 23 clean images that the measurement also uses. The hints are
general (a signature in any style, a name without a title, contact details in a letterhead), but a
result on these images may still be better than on unseen documents. The 14 images with a labelled
error were not used for the change, and the report states this limitation.
