# 0005 — Document storage: consent first, envelope encryption, deletion with the file
Date: 2026-11-10 · Status: Proposed (to be confirmed with the advisor)

## Context
Week 9 ends with document upload and deletion (FR-07, FR-11). Applicants upload copies of
passports, bank statements and payslips. NFR-01 asks for explicit consent before the first
upload, encryption at rest, a limited retention period and deletion on request; NFR-09 limits
uploads to PDF, JPEG and PNG of at most 10 MB. ADR 0002 replaced an object store with a small
storage interface over a local volume. The fall prototype runs on one machine with Docker
Compose; there are no backups and no real personal documents in development or tests.

## Decision
1. **Consent before the first upload.** The consent text has a version (`consent-v1`, Turkish and
   English, in the client's translation files). Accepting it writes a `consents` row (user,
   version, given_at). Upload is refused with `403` unless the user has a valid consent for the
   current version; a new version asks again. Withdrawing consent sets `withdrawn_at` and deletes
   all of the user's documents (decision 5).
2. **Envelope encryption with AES-256-GCM.** Each document gets a random 256-bit data key and is
   encrypted with AES-GCM (`cryptography`, Apache-2.0/BSD licence); every encrypted value
   (file, name, wrapped key) starts with its own random 96-bit nonce. The document ID is bound
   as associated data, so a file cannot be swapped under another record. The data key is itself
   encrypted ("wrapped") with a master key and stored in the `documents` row with the ID of that
   master key. The master key is 32 random bytes in `.env` (`DOCUMENT_MASTER_KEY`, base64), never
   in the repository; a missing key stops the API at start-up. Rotating the master key re-wraps
   the data keys, not the files.
3. **Storage.** Encrypted files are written to the storage volume under a random name
   (`storage_key`, a UUID), never under the original file name. The original name is kept only
   encrypted, with the same data key, because names like `ayse_yilmaz_passport.pdf` are personal
   data. The database stores type, size, the SHA-256 of the plain file (needed in spring to cache
   extraction results, ADR 0003) and the dates. Files are written to a temporary name and renamed
   when complete, so a failed upload leaves no half-written file.
4. **Validation before storing.** At most 10 MB, checked while reading; the type is taken from the
   file's first bytes (PDF `%PDF-`, JPEG `FF D8 FF`, PNG `89 50 4E 47`), not from the name or the
   browser's content type; anything else is refused with `415`. Location data in photos (EXIF)
   is removed when phone-camera upload is added in week 11.
5. **Deletion.** Deleting a document removes its row and its encrypted file at once; deleting an
   application file, withdrawing consent or deleting the account does the same for all their
   documents. Because the data key lives only in the row, a file left on disk by a crash cannot
   be decrypted; a cleanup command removes such orphans. **Retention:** `delete_after` is the
   trip end plus 30 days (proposal; open question to the advisor), and a daily command deletes
   expired documents.
6. **Download only by the owner.** A document is decrypted while it is sent, only to its owner
   (404 for anyone else, as in ADR 0004), with `Content-Disposition: attachment`,
   `X-Content-Type-Options: nosniff` and `Cache-Control: no-store`.

## Alternatives considered
- **Disk encryption only (FileVault, an encrypted volume):** protects a stolen laptop but not a
  copied volume, a backup or a mistake in file permissions; NFR-01 asks for encryption by the
  application.
- **Files in the database (`bytea`):** one place to delete from, but the database and its dumps
  grow with every scan, and the storage interface of ADR 0002 would be bypassed.
- **Object store with server-side encryption (MinIO, S3):** the target for production; deferred by
  ADR 0002. The storage interface keeps the move to one class.
- **Fernet (`cryptography`) with one key for all files:** simpler, but one key for everything means
  rotation re-encrypts every file, and there is no per-document key to destroy with the row.

## Consequences
- New tables `consents` and `documents` as in `docs/design/data-model.md`, plus `wrapped_key`,
  `key_id` and `original_name_encrypted` on `documents`; one migration.
- One new dependency: `cryptography`. `DOCUMENT_MASTER_KEY` and `STORAGE_DIR` in `.env.example`;
  a command prints a new random master key.
- Losing the master key makes all documents unreadable; this is accepted for the prototype
  (applicants keep their originals) and stated in the README.
- Tests use a temporary storage directory and a test key; they cover consent, type and size
  checks, round trip, tampering (a changed byte fails decryption), access by another user, and
  that deletion removes the file from disk.
