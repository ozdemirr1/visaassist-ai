# Official Source Inventory

Version 0.1 · reviewed 2026-10-23 · Machine-readable list: [`data/sources.yaml`](../data/sources.yaml)

Every requirement and rule in VisaAssist AI cites one of the sources below (NFR-03). The pilot
uses two layers (ADR 0001 and its amendment of 23 October 2026):

1. **EU baseline** shared by all Schengen states for applicants in Türkiye.
2. **National layer** per destination: the Netherlands (main pilot destination) and Norway
   (second layer, for the translation requirement).

Snapshots of all sources are captured with `python -m app.sources.snapshot` and stored in
`data/snapshots/` with a SHA-256 hash and the retrieval time (see [Snapshots](#snapshots)).

## 1. Sources

| ID | Source | Layer | Format | Date stated by the source | Reviewed |
| --- | --- | --- | --- | --- | --- |
| `eu-harmonised-list-tr` | [Commission Implementing Decision C(2021) 5156, Annex III — supporting documents for applicants in Türkiye](https://udiregelverk.no/contentassets/82b696de16f6403a9c5a2b62b91e0683/c_2021_5156_annex-iii.pdf) | EU | PDF | 29 Jul 2021 | 23 Oct 2026 |
| `nl-checklist-tourism-tr` | [NetherlandsWorldwide — Checklist: Schengen visa in Türkiye for tourism](https://www.netherlandsworldwide.nl/visa-the-netherlands/checklist-schengen-visa-tourism/turkiye) | NL | HTML | published 20 Aug 2025, modified 28 Aug 2025 | 23 Oct 2026 |
| `nl-apply-tr` | [NetherlandsWorldwide — Applying for a Schengen visa in Türkiye](https://www.netherlandsworldwide.nl/visa-the-netherlands/schengen-visa/apply-turkiye) | NL | HTML | — | 23 Oct 2026 |
| `no-checklist-c-visa-tr` | [Royal Norwegian Embassy in Ankara — Visa Application Checklist Turkey, All Categories](https://www.norway.no/contentassets/aa2ef9f22e8846c681cd15c9d6c60e09/checklist-turkey-january-2025.pdf) | NO | PDF | none inside the document; file name "january-2025" | 23 Oct 2026 |
| `no-visitors-visa-tr` | [Royal Norwegian Embassy in Ankara — Visitor's visa](https://www.norway.no/en/turkiye/services-info/visitors-visa-res-permit/visitors-visa/) | NO | HTML | — | 23 Oct 2026 |

The EU decision is read from the copy published by the Norwegian Directorate of Immigration
(UDI), because the Commission does not publish the Türkiye annex as a separate page. The
Norwegian checklist is the one linked as "Checklist for C-visa" from the embassy's Visitor's
visa page on the review date.

## 2. Requirements per source

Passages are paraphrased; the rule file cites the source ID and the section.

### EU baseline (`eu-harmonised-list-tr`)
- **Financial means:** bank statement of the last three months showing regular income, **and**
  proof of regular income such as salary slips of the last three months; pension booklet if relevant.
- **All applicants:** travel arrangements, complete civil registry extract (*Tam Tekmil Vukuatlı
  Nüfus Kayıt Örneği*), proof of accommodation.
- **Employees:** employer letter and/or leave approval addressed to the consulate (name, passport
  number, start date, job, length of leave and whether paid, employer contacts, signatory);
  SGK employment statement and SGK registration and service record with a readable QR code.
- **Students:** YÖK student certificate with a readable QR code (higher education).
- **Language:** no statement about translations.

### Netherlands (`nl-checklist-tourism-tr`)
- **Passport:** issued within the last 10 years, at least 2 empty pages, signed, valid at least
  3 months after leaving the Schengen area.
- **Photo:** colour, not older than 6 months, 35 × 45 mm, light background (not needed when the
  external service provider takes it).
- **Financial means:** bank statements of the last 3 months, proof of income or pension booklet.
- **Insurance:** covers all Schengen states and the whole stay, at least EUR 30,000 including repatriation.
- **Employees / students:** as in the EU baseline (employer letter with listed contents, SGK
  documents with readable QR code; YÖK certificate with readable QR code).
- **Language:** no statement about translations.

### Norway (`no-checklist-c-visa-tr`, `no-visitors-visa-tr`)
- **Translation (general rule):** "All documents must be translated into English or Norwegian."
  The checklist does not say whether the translation must be certified or sworn. The embassy
  page words it more narrowly ("certain documents, according to the relevant checklist") and
  warns that untranslated documents can lead to longer processing or refusal.
- **Document age (general rule):** no supporting document older than 6 months.
- **Passport:** valid at least 3 months beyond the intended stay, at least 2 blank pages.
- **Financial means:** salary slips of the last three months and bank statement movements of the
  last three months; alternatively at least NOK 500 per person per day, documented for the
  past six months; sponsor form if a private person covers the costs.
- **Insurance:** whole Schengen area, at least EUR 30,000, for the full period applied for.
- **Employees / students:** same documents as the EU baseline; civil registry extract with QR code.

## 3. Findings for the pilot

1. **Translation requirement — resolved.** The Norwegian checklist provides the official basis
   for the missing-translation check. The check verifies that a translation into English or
   Norwegian is present for each document; it does **not** check certification, because the
   source does not require it. The rule applies only to applications for Norway.
2. **Payslips come from the EU baseline.** The Netherlands page asks for "proof of income"; the
   three-month salary slip requirement in ADR 0001 is taken from C(2021) 5156. The rule file
   cites the EU source for it.
3. **Norway's checklist is not dated inside the document.** Versions are therefore identified by
   the snapshot hash and retrieval date, not by a date printed on the source. This satisfies the
   ADR 0001 amendment: Norway is confirmed as the second destination.
4. **Differences between the two national layers** (useful for the report and for showing why a
   generic answer is not enough):

| Topic | Netherlands | Norway |
| --- | --- | --- |
| Translation | not required | all documents in English or Norwegian |
| General document age | not stated (photo ≤ 6 months) | no document older than 6 months |
| Passport validity | 3 months after leaving the Schengen area | 3 months beyond the intended stay |
| Financial means | bank statements 3 months *or* proof of income | salary slips *and* bank movements 3 months, or NOK 500/day over 6 months |

## 4. Snapshots

- Run weekly (Mondays) from `backend/`: `uv run python -m app.sources.snapshot`. From spring
  week B1 the job queue takes over the schedule (ADR 0002).
- A file is stored only when the content hash changes; every attempt is logged in
  `data/snapshots/manifest.jsonl` (time, HTTP status, hash, size, file).
- Stored versions are the raw data for change detection (FR-16) and for labelling meaningful
  versus cosmetic changes (AS3). HTML pages often change in non-content parts (scripts, menus),
  which is exactly the cosmetic case AS3 has to separate.

## 5. Review procedure
- Re-read every source when its snapshot changes and at least once a month.
- Record the review date in `data/sources.yaml` (`reviewed_on`) and here.
- A changed requirement is updated in the rule file in a pull request that names the snapshot.
