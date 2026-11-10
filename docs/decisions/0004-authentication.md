# 0004 — Authentication: e-mail and password, opaque session token in an HttpOnly cookie
Date: 2026-11-10 · Status: Proposed (to be confirmed with the advisor)

## Context
Week 9 builds accounts, application files and document upload (FR-04, FR-05, FR-07). Users
register and log in with the roles applicant and administrator (FR-04). NFR-02 asks for salted
password hashes, token-based authentication and access to one's own files only. The files hold
copies of passports, bank statements and payslips, so a stolen login is the most serious risk of
the fall prototype. Constraints: one developer, no e-mail service in the fall, the web client and
the API served from the same site (Vite proxy in development, Nginx in spring, ADR 0002), and
everything testable in CI without external services.

## Decision
1. **E-mail and password.** Passwords are hashed with Argon2id (`argon2-cffi`, MIT licence) with
   the library's default parameters; at least 10 characters; the e-mail is stored lower-cased and
   unique.
2. **Opaque session token in a cookie.** On login the API creates 32 random bytes
   (`secrets.token_urlsafe`), stores only their SHA-256 in a `sessions` table (user, created,
   last seen, expires) and sends the token as a cookie: `HttpOnly`, `Secure` (except on
   localhost), `SameSite=Lax`, path `/`. Sessions expire after 7 days, or after 2 days without
   use. Logout, password change and account deletion delete the sessions. This is the token of
   NFR-02; it is checked on every request by one FastAPI dependency (`current_user`).
3. **Cross-site requests.** `SameSite=Lax` keeps the cookie off cross-site form posts; in
   addition every state-changing request (`POST`, `PUT`, `PATCH`, `DELETE`) must carry the header
   `X-Requested-With: visaassist`, which a cross-site form cannot set without a CORS preflight,
   and CORS allows only the client's own origin.
4. **Own files only.** Every query on application files and documents filters by the current
   user's ID in the data-access function itself, not in the route; a file of another user returns
   404, not 403, so its existence is not revealed. Tests cover access by a second user for every
   route.
5. **Roles.** A `role` column (`applicant`, `admin`). Registration always creates applicants; an
   administrator is created with a command-line command (`python -m app.users.create_admin`).
6. **Brute force.** Failed logins are counted per e-mail and per IP address in the database; after
   5 failures in 15 minutes further attempts wait 15 minutes. Error messages do not say whether
   the e-mail exists.
7. **Deferred:** e-mail verification and password reset need an e-mail service and move to the
   spring with the production setup; until then an administrator can reset a password from the
   command line. Two-factor authentication is out of scope.

## Alternatives considered
- **JWT access token kept in `localStorage`:** common in tutorials, but any injected script can
  read it, and a JWT cannot be revoked before it expires without a server-side list — which is a
  session table again.
- **JWT in an HttpOnly cookie:** removes the script access but keeps the revocation problem and
  adds key management; no second service needs to verify tokens without the database.
- **Sign-in with Google or another identity provider:** no password storage, but an external
  dependency in tests and demos, a privacy notice for a third party (NFR-01), and not every
  applicant wants to link a Google account to visa documents.
- **Passwordless login by e-mail link:** good usability, but needs an e-mail service in the fall.
- **An authentication library (for example fastapi-users):** saves code but brings its own data
  model and many options; the parts needed here are a few small, well-tested functions that are
  easier to explain in the report.

## Consequences
- New tables `users` (if not yet created), `sessions` and `login_attempts`; one migration.
- One new dependency: `argon2-cffi` (backend). The client needs no token handling; it sends
  requests with `credentials: "include"` and the custom header.
- The cookie works only when the client and API are on the same site; a separate API domain
  would require revisiting decision 3.
- Tests: registration, login, wrong password, lockout, logout, expiry, access to another user's
  file, the custom header on state-changing requests, role checks.
