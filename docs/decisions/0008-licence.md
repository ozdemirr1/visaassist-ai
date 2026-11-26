# 0008 — Licence of the public repository
Date: 2026-11-23 · Status: Accepted

## Context
The repository is public so that the advisor, the course staff and the jury can review the code,
the data and the documents (agreed with the advisor on 20 November 2026). Until now it had no
licence file. A public repository without a licence already reserves all rights by default, but
that is easy to misread; the README said only that no licence had been chosen.

Who may use the work later is not settled yet: the university's technology transfer office (TTO)
was asked on 23 November 2026 about the ownership of a senior design project; there is no answer
yet. An open-source licence, once granted, cannot be taken back for the copies already made.

## Decision
The repository carries a `LICENSE` file that reserves all rights: the work is public for academic
review, and it may not be used, copied, modified or distributed without the author's written
permission. Third-party components keep their own licences; passages quoted from official sources
belong to their publishers. The README states the same in its Licence section. The standards and
regulations the system applies are listed in `docs/standards.md` (added in the same change, #112).

## Alternatives considered
- MIT or Apache-2.0: would let anyone reuse the work at once; not chosen while ownership is open,
  because the grant cannot be withdrawn later.
- No licence file: legally the same reservation, but unclear to a reader of the repository.
- A private repository: would make the review by the course staff and the jury harder.

## Consequences
The review works as before. Reuse by others needs the author's permission. If the TTO answers that
the university holds rights, or the author later chooses an open-source licence, this ADR is
superseded by a new one and the `LICENSE` file is replaced in the same pull request.

## Amendment, 26 November 2026: the TTO's answer
The university's technology transfer office answered on 26 November 2026: under the Law on
Intellectual and Artistic Works (FSEK, Law No. 5846) a computer program is a work whose rights
belong to its author, so the university claims no rights to the code; the university's claims and
the duty to notify apply to inventions, and a program alone is not an invention. For a later
commercial use the office advised keeping the code confidential. The author decided to keep the
repository public for the course review, under "all rights reserved", accepting that public code
can be read and copied in breach of the licence; the decision can be revisited before any
commercial step, and the office offered to help with the road map then.
