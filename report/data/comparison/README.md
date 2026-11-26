# Model alone against model + rule engine

`2026-11-26_gpt-6.2-sol_3runs.jsonl` holds one line per run, system and case (`Outcome` in
`backend/app/demo/compare.py`): 3 runs × 2 systems × 19 cases = 114 lines. The cases are the two
demo files without errors and each of the 17 labelled errors applied alone; both systems received
the same rendered SAMPLE images. Model `gpt-6.2-sol`, 26 November 2026; reading prompt
`extract-v2` (frozen on 23 November, see `../extraction/README.md`); model-alone prompt
`compare-v1`.

## Result (report, Table "model-comparison")

| | Model alone | Model + rule engine |
| --- | --- | --- |
| Labelled errors found (of 17), per run, automatic count | 17, 17, 17 | 17, 17, 17 |
| Labelled errors found, after reading the model's hits | 16, 16, 16 | 17, 17, 17 |
| Further findings on the 2 error-free files, per run | 15, 16, 17 | 0, 0, 0 |
| Further findings in the 17 error cases, per run | 115, 107, 100 | 0, 0, 0 |
| Cost per file, list price (every document of the file read) | USD 0.078 | USD 0.088 |
| Time per file | 21.2 s | 28.1 s |

The cost per file of the rule-engine side counts each document as read for that file. In a run
each image was read once and reused across the cases that contain it, so the money actually spent
on that side was lower than 19 × 0.088.

## Reading the model-alone hits

The automatic count accepts a model-alone answer as a hit when it names the document the error
changed. Every such hit of the three runs was read (26 November 2026). All describe the labelled
error except S01 (the Norwegian bank statement without a translation): in all three runs the
"hits" on the bank statement were about a missing bank officer's signature and the source of a
salary credit, never the translation. S01 is therefore counted as missed.

## The further findings of the model alone

370 in three runs (6.5 per file). Grouped by keyword, then read:

| Theme | Count | Reading |
| --- | --- | --- |
| Bank statement without an officer's signature or authentication | 102 | not required by the official sources |
| Translation gives only the name and the issue date | 79 | true of the simplified synthetic translations |
| Employer's full address, telephone or e-mail missing | 54 | beyond the sources; the letterhead gives company and city |
| Source of the salary credits, payslips against credits | 36 | partly a real inconsistency of the demo data (credits and pay dates do not all line up) |
| Insurance wording (emergency, repatriation not spelled out) | 18 | beyond what the certificate needs to state |
| Application form shows only some fields | 5 | true of the abbreviated synthetic form |
| Photo | 3 | — |
| Machine-readable zone check digit "wrong" | 1 | wrong: the check digit is correct |
| Other (partial SGK records, SAMPLE marking, civil registry layout) | 72 | mostly simplifications of the synthetic documents |

So most further findings are not mistakes of the model: they ask for more than the sources
require, or point at simplifications of the synthetic documents, which the rule engine does not see
either. For an applicant each is still a point to check without knowing whether a consulate would
raise it; the rule engine reports only what a cited source requires.
