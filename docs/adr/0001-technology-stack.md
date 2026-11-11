# ADR-0001: Technology stack for Alfulk

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** CTO
- **Supersedes:** —

## Context

Alfulk is a self-hosted replacement for Google's account platform: one identity
for sign-in, profiles and organizations, plus Drive (files) and Mail. The
roadmap is M0 Foundations → M1 Identity & Sign-in → M2 Admin & Orgs → M3 "Sign
in with Alfulk" (OIDC provider) → M4 Drive → M5 Mail.

That shape puts specific weight on the stack choice:

- **Identity is the first module and the hardest to get wrong.** Password
  hashing, session management, CSRF, two-factor and account recovery are
  places where writing it ourselves is a liability. We want a framework where
  these are solved, audited and maintained by other people.
- **Self-hosted is the product, not the deployment.** Operators will run this
  themselves. A stack that needs a managed cloud service to function is a
  product defect, not just an ops preference.
- **Six modules, one team.** Admin, orgs, Drive and Mail are all
  CRUD-with-permissions over a relational model. A framework with a strong
  ORM, migrations, an admin and a mature permissions story removes a lot of
  repeated work.
- **M3 ships an OIDC provider**, so we will need a stack with a credible,
  maintained OAuth2/OIDC server library rather than hand-rolled token issuance.

The board proposed a starting stack. This ADR adopts it, with the additions
and the one substitution noted under "Decision".

## Decision

### Language and framework

- **Python 3.12+**, **Django 5.2 LTS**. Django 5.2 is a long-term-support
  release, so we get security fixes without a framework upgrade landing in the
  middle of M4 or M5. Pin to `>=5.2,<5.3`.
- **Server-rendered Django templates. No SPA in increment 1.** Sign-up,
  sign-in, two-factor enrolment and the account page are form-and-redirect
  flows. Django's forms, CSRF protection and messages framework cover them,
  and keeping the browser dumb removes a whole class of token-handling bugs
  from the module where we can least afford them. If a later module (Drive's
  uploader is the likely first) needs real interactivity, we add progressive
  enhancement — htmx or small islands of vanilla JS — and record that in a new
  ADR. We do not pre-emptively adopt a frontend build chain.

### Data

- **PostgreSQL 16+** as the only datastore, accessed through `psycopg` 3.
  Chosen over MySQL for `jsonb`, partial and expression indexes, proper
  transactional DDL, and row-level locking semantics we will want for Drive
  quotas. Chosen over SQLite because staging and production need concurrent
  writers.
- **No cache or broker in increment 1.** Sessions go in the database. Redis
  and a task queue arrive when a module actually needs them — Drive
  thumbnailing or Mail delivery — and get their own ADR. Adding them now buys
  a second stateful service to operate and nothing else.

### Authentication and cryptography

- **Argon2id** for password hashing, via Django's `Argon2PasswordHasher` and
  `argon2-cffi`. Listed first in `PASSWORD_HASHERS` so Django transparently
  upgrades any legacy hash on next sign-in. Parameters are set explicitly in
  settings rather than left to library defaults, so a tuning change is a
  reviewable diff.
- **TOTP two-factor via `pyotp`** (RFC 6238), with QR enrolment rendered
  server-side by `qrcode`. We deliberately do not pull in a batteries-included
  two-factor package: the flows we need are narrow, and the stored secret is
  the most sensitive row in the database, so we want the storage and
  verification code to be ours and reviewed.
- **TOTP secrets encrypted at rest** with Fernet (AES-128-CBC plus an
  HMAC-SHA256 tag, from `cryptography`), using `MultiFernet` over an ordered
  per-environment key list so rotation re-encrypts rather than invalidates.
  A TOTP secret is unlike a password hash: verification needs the original
  value back, so hashing is not available and the plaintext would otherwise
  sit in the database. **Be honest about what this buys:** it defends against
  a database-only compromise — a leaked dump, a backup on the wrong disk, a
  SQL injection read — and it does *not* defend against an attacker who can
  run code on the application host, because that host must hold the key. The
  key therefore lives in the environment, never in the database, and never in
  the same store as the database credentials.
- **One-time recovery codes stored as HMAC-SHA256 hashes**, keyed by a
  dedicated `RECOVERY_CODE_HMAC_KEY` that is separate from `SECRET_KEY`.
  HMAC rather than a slow password hash is correct here: recovery codes are
  high-entropy values we generate, so there is nothing to brute-force offline,
  and a keyed hash means a database leak alone does not let an attacker test
  candidate codes. Codes are shown exactly once, at generation.
  Key rotation invalidates outstanding codes; that is the intended behaviour
  and must be stated in the operator docs.
- **Sessions in secure cookies** backed by database-stored session data, with
  `Secure`, `HttpOnly`, `SameSite=Lax`, session rotation on privilege change,
  and an idle timeout. Database-backed sessions let an admin revoke a session,
  which cookie-only sessions cannot do and M2 will require.

### M3 forward-looking note

For the OIDC provider in M3 the current intent is to build on a maintained
OAuth2/OIDC server library rather than issue tokens by hand. That choice is
**not** made here — it gets its own ADR when M3 starts — but it is a reason to
stay on mainstream Django rather than a niche framework: the library ecosystem
for "Django as an OIDC provider" is real, and the alternatives' is not.

### Developer tooling

- **`ruff`** for both linting and formatting. One tool, one config block in
  `pyproject.toml`, no `black`/`isort`/`flake8` triangle to keep in sync.
- **Django's own test runner** with `unittest`-style tests, run against a real
  PostgreSQL instance in CI. Not pytest: the built-in runner is one less
  dependency, and Django's `TestCase` transaction handling and test client are
  what we actually use.
- **`coverage.py`** with a floor enforced in CI, ratcheted upward over time
  rather than set aspirationally high on day one.
- **Dependencies declared in `pyproject.toml`**, installed with `pip`.
  Reproducible builds need a lockfile; generating one requires a Python
  environment, so it is tracked as a separate foundation task rather than
  guessed at here.
- **Docker Compose** for local development, providing PostgreSQL so no
  engineer has to install it. The application itself runs on the host during
  development.
- **GitHub Actions** for CI — see [ADR-0004](0004-ci-cd-and-branching.md).

## Alternatives considered

- **Django with a React/Vue SPA.** Rejected for increment 1. It adds a build
  pipeline, a second deployment artifact, and the need to hold authentication
  state in the browser, all to improve flows that are inherently
  navigation-based. The cost lands exactly on the module with the highest
  security stakes.
- **FastAPI + SQLAlchemy.** Faster for pure JSON APIs, but we would hand-build
  sessions, CSRF, forms, the admin and the permission model. For a product
  that is mostly authenticated CRUD with an HTML frontend, that is a large
  volume of security-relevant code we would own and Django already owns.
- **Rails.** A genuinely comparable fit. Rejected on team and ecosystem
  grounds rather than technical ones; the Python ecosystem is also where the
  usable OIDC-provider and IMAP/SMTP libraries we will want in M3 and M5 live.
- **`bcrypt` instead of Argon2id.** Rejected: bcrypt silently truncates
  passwords beyond 72 bytes and has no memory-hardness. Argon2id is the
  current recommendation and Django supports it first-class.
- **Storing recovery codes with Argon2.** Rejected: slow hashing protects
  low-entropy human-chosen secrets. Recovery codes are machine-generated with
  ample entropy, so the slowness buys nothing and costs us a timing problem on
  the sign-in path; a keyed HMAC gives the property we actually want.
- **A ready-made Django two-factor package.** Rejected for M1 — see above. We
  may revisit if the flows grow beyond TOTP plus recovery codes.
- **MySQL / MariaDB.** Rejected: weaker JSON and indexing support, and
  non-transactional DDL makes migrations riskier.

## Consequences

- We accept Django's conventions, including its migration system and its
  request/response cycle. Deviating from them later is expensive.
- Server-rendered templates mean any genuinely interactive feature needs a
  deliberate decision and a new ADR, rather than arriving by default.
- Hand-rolling TOTP and recovery-code storage means that code needs careful
  security review. It is explicitly in scope for the Code Reviewer / Security
  Engineer on every pull request that touches it.
- Running without Redis or a task queue means any increment-1 work that wants
  background processing has to be reconsidered or deferred.
- `RECOVERY_CODE_HMAC_KEY` and `TOTP_SECRET_ENCRYPTION_KEYS` are new
  operational secrets with their own rotation consequences. Both must exist in
  every environment before M1 ships. Rotating the HMAC key invalidates
  outstanding recovery codes; rotating the Fernet key list does not invalidate
  anything, but the old key must stay in the list until a re-encryption pass
  has run.
- Losing `TOTP_SECRET_ENCRYPTION_KEYS` locks every user out of their second
  factor with no recovery path short of recovery codes. It belongs in the
  backup and key-escrow procedure, not only in the deploy environment.
- No lockfile on day one means CI resolves dependency versions within the
  declared ranges. This is a known gap, closed by the lockfile foundation task.
