# Data Model

Version 0.1 · 2026-10-23 · Basis for the week 7 models and migrations (SQLAlchemy 2, PostgreSQL 17)

The model follows the requirement files (`data/requirements/`) and the source registry
(`data/sources.yaml`). Tables marked *spring* are designed now so that the fall schema does not
have to change shape later, but they are created only when the feature is built.

## 1. Principles
1. **YAML is the source of truth for requirements; the database holds a versioned copy.** The
   loader validates the files (`app.requirements.loader`) and writes them as one
   `requirement_set` identified by the hash of the files. A check run records the set it used, so
   an old finding can always be explained with the rule that produced it, even after a source
   change (FR-10, FR-16).
2. **Rule parameters are stored as JSON, validated by the Pydantic schema.** Twelve check kinds
   with different parameters do not get a column each; `rules.check` is `jsonb` and is only ever
   written from a validated `Check` model.
3. **Field values are typed by the document catalog.** `document_field_values.value` is `jsonb`
   holding the value in the form its field type defines (date as ISO string, money as
   `{amount, currency}`), together with where it came from: entered by the applicant (fall) or
   extracted with a confidence (spring, FR-13).
4. **Personal data is minimal and deletable** (NFR-01). Files are stored encrypted under random
   keys, never under the original file name; deleting a document removes the file, its field
   values and the findings that cite it. Application files are hard-deleted on request (FR-11).
5. **IDs:** UUIDs for everything users create; the readable text IDs of the YAML files
   (`nl-rule-photo-age`) for sources, document types, requirements and rules.

## 2. Diagram

```mermaid
erDiagram
    USER ||--o{ CONSENT : gives
    USER ||--o{ APPLICATION_FILE : owns
    APPLICATION_FILE ||--o{ APPLICATION_EVENT : "moves through steps"
    APPLICATION_FILE ||--o{ DOCUMENT : contains
    DOCUMENT ||--o{ DOCUMENT_FIELD_VALUE : has
    APPLICATION_FILE ||--o{ CHECK_RUN : "is checked by"
    CHECK_RUN ||--o{ FINDING : produces
    FINDING }o--o{ DOCUMENT : cites

    REQUIREMENT_SET ||--o{ REQUIREMENT : contains
    REQUIREMENT_SET ||--o{ RULE : contains
    REQUIREMENT_SET ||--o{ CHECK_RUN : "used by"
    APPLICATION_FILE }o--|| REQUIREMENT_SET : "checklist from"
    DOCUMENT_TYPE ||--o{ DOCUMENT_FIELD : defines
    DOCUMENT_TYPE ||--o{ REQUIREMENT : "asked for by"
    DOCUMENT_TYPE ||--o{ DOCUMENT : "type of"
    REQUIREMENT ||--o{ DOCUMENT : "fulfilled by"
    RULE ||--o{ FINDING : "reported by"
    REQUIREMENT ||--o{ FINDING : "missing document"

    SOURCE ||--o{ SOURCE_SNAPSHOT : "captured as"
    SOURCE ||--o{ REQUIREMENT : cited
    SOURCE ||--o{ RULE : cited
    SOURCE ||--o{ SOURCE_CHANGE : "changes (spring)"
    SOURCE_CHANGE ||--o{ NOTIFICATION : "triggers (spring)"
    USER ||--o{ NOTIFICATION : receives

    USER {
        uuid id PK
        text email UK
        text password_hash
        text role "applicant | admin"
        text language "tr | en"
        timestamptz created_at
    }
    CONSENT {
        uuid id PK
        uuid user_id FK
        text version "consent text version"
        timestamptz given_at
        timestamptz withdrawn_at "null while valid"
    }
    APPLICATION_FILE {
        uuid id PK
        uuid user_id FK
        text destination "NL | NO"
        text visa "schengen-c"
        text purpose "tourism"
        text profile "employed | student"
        date trip_start
        date trip_end
        date application_date "reference date for age rules"
        text step "draft | appointment | documents | submitted | decided"
        text requirement_set_id FK
        timestamptz created_at
    }
    APPLICATION_EVENT {
        uuid id PK
        uuid application_file_id FK
        text step
        timestamptz occurred_at
    }
    DOCUMENT {
        uuid id PK
        uuid application_file_id FK
        text requirement_id FK
        text document_type_id FK
        text storage_key "random, encrypted file"
        text mime_type
        int size_bytes
        text sha256
        text language "ISO 639-1"
        text translation_language "null if none"
        timestamptz uploaded_at
        timestamptz delete_after "retention"
    }
    DOCUMENT_FIELD_VALUE {
        uuid document_id PK, FK
        text field_id PK
        jsonb value
        text origin "entered | extracted"
        real confidence "spring"
        timestamptz confirmed_at
    }
    CHECK_RUN {
        uuid id PK
        uuid application_file_id FK
        text requirement_set_id FK
        timestamptz started_at
        timestamptz finished_at
        text status "running | done | failed"
    }
    FINDING {
        uuid id PK
        uuid check_run_id FK
        text rule_id FK "null for a missing document"
        text requirement_id FK "set for a missing document"
        text severity "error | warning"
        jsonb details "documents, fields, values compared"
    }
    REQUIREMENT_SET {
        text id PK "hash of the YAML files"
        text git_commit
        timestamptz loaded_at
        bool active
    }
    DOCUMENT_TYPE {
        text id PK
        text title_en
        text title_tr
        bool multiple
    }
    DOCUMENT_FIELD {
        text document_type_id PK, FK
        text field_id PK
        text type
        text title_en
        text title_tr
        bool optional
    }
    REQUIREMENT {
        text requirement_set_id PK, FK
        text id PK
        text destination "null for the EU layer"
        text document_type_id FK
        text_array profiles
        text submit_as
        text source_id FK
        text section
        text passage
        text basis "stated | derived"
    }
    RULE {
        text requirement_set_id PK, FK
        text id PK
        text destination "null for the EU layer"
        text severity
        text_array profiles
        jsonb check "validated Check model"
        text title_en
        text title_tr
        text source_id FK
        text section
        text passage
        text basis
    }
    SOURCE {
        text id PK
        text title
        text publisher
        text layer
        text destination
        text url
        text format
        date source_date
        date reviewed_on
    }
    SOURCE_SNAPSHOT {
        uuid id PK
        text source_id FK
        timestamptz retrieved_at
        text status "new | changed | unchanged | error"
        text sha256
        int bytes
        text file
    }
    SOURCE_CHANGE {
        uuid id PK
        text source_id FK
        uuid from_snapshot_id FK
        uuid to_snapshot_id FK
        text classification "meaningful | cosmetic"
        text summary
        text status "pending | approved | rejected"
        uuid reviewed_by FK
    }
    NOTIFICATION {
        uuid id PK
        uuid user_id FK
        uuid application_file_id FK
        uuid source_change_id FK
        text channel "email | in_app"
        timestamptz sent_at
        timestamptz read_at
    }
```

## 3. Tables by semester

| Table | Fall | Spring | Requirement |
| --- | --- | --- | --- |
| `users`, `consents` | ✓ | | FR-04, NFR-01 |
| `application_files`, `application_events` | ✓ | | FR-05, FR-06 |
| `documents`, `document_field_values` | ✓ | extraction fields (`origin`, `confidence`) used | FR-07, FR-08, FR-13 |
| `check_runs`, `findings` | ✓ | | FR-09, FR-10 |
| `requirement_sets`, `requirements`, `rules`, `document_types`, `document_fields` | ✓ (loaded from YAML) | admin editing (FR-18, see open questions) | FR-02 |
| `sources`, `source_snapshots` | ✓ (imported from `data/`) | | NFR-03, AS3 |
| `source_changes`, `notifications` | | ✓ | FR-16, FR-17 |
| Synthetic dataset and evaluation runs | | ✓, separate `research` schema | FR-22, AS1–AS2 |

## 4. How the main flows use the model
- **Checklist (FR-02):** `requirements` of the active set where `destination` is null or the
  file's destination and the profile is in `profiles`, joined with `document_types` for titles in
  the user's language and with `sources` for the link.
- **Upload (FR-07):** a `documents` row per file, linked to the checklist item it fulfils; the
  file is encrypted and stored under `storage_key`; `delete_after` is set from the retention period.
- **Field entry (FR-08):** one `document_field_values` row per field, validated against
  `document_fields.type`; `origin = entered`, `confirmed_at` set on save.
- **Check run (FR-09, FR-10):** a `check_runs` row with the file's requirement set; every missing
  document gives a finding with `requirement_id`, every failed rule a finding with `rule_id`;
  `details` holds the documents, fields and values compared, so the finding page needs no
  re-computation.
- **Source change (spring, FR-16, FR-17):** a `source_changes` row between two snapshots; on
  approval a new requirement set is loaded; files on the old set whose findings change get a
  `notifications` row (`docs/positioning.md`, section 2.1).

## 5. Open questions
- **Retention period** for uploaded documents (NFR-01): proposal 30 days after `trip_end`, or on
  request earlier. To decide with the advisor.
- **Admin editing of requirements in spring (FR-18):** keep YAML + pull request as the only way
  (simple, reviewed, versioned) or edit in the web application and export to YAML. Decide in B9.
- **Applicant's own name variants** (e.g. Turkish characters in bookings, *Ş* vs *S*): matching
  rules belong in the rule engine, not the schema; noted here because it affects `details`.
