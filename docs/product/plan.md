# Alfulk product plan

Status: draft for confirmation (owner: Product Manager). Last updated 2026-11-11.

## Vision

Alfulk is a self-hosted replacement for Google's account platform. One account
signs you in everywhere, holds your profile and your organization memberships,
stores and shares your files (Drive), and sends and receives your mail (Mail).

The operator runs it on their own infrastructure and keeps the data. The
experience should feel as safe and as boring as a Google account: sign-up and
sign-in just work, two-factor is easy to turn on, and nothing surprising happens
to your data.

Principles that shape every increment:

- **One identity.** Every module authenticates through the same account and the
  same session. No module ships its own login.
- **Secure by default.** Strong password hashing, secure cookies, two-factor,
  lockout, and an audit trail arrive in increment 1, before any feature that
  stores user data.
- **Small, verifiable increments.** Each increment has written acceptance
  criteria and is checkable on staging with synthetic data before release.
- **Server-rendered and self-hostable.** Plain HTML pages, one database, no
  mandatory third-party services. (Stack decisions live in `docs/adr/`.)

## Users

| User | What they need from Alfulk | First served in |
| --- | --- | --- |
| End user | One account to sign in, manage their profile, store and share files, and send and receive mail. | M1 (sign-in), M4 (files), M5 (mail) |
| Org admin | Create an organization, manage its users and groups, assign roles, enforce two-factor, and read an audit log. | M2 |
| Developer | "Sign in with Alfulk" for their own applications via a standard OpenID Connect provider. | M3 |
| Operator (implicit) | Install, configure, upgrade, and back up a single self-hosted deployment. | M0 foundations, every increment |

## Module roadmap

Modules ship in order. Each module is delivered as one or more increments, each
with its own brief under `docs/product/`.

### M0 Foundations (engineering, owned by the CTO)

Repository scaffold, stack and hosting decisions as ADRs, environments
(preview, staging, production), CI and the pull-request flow. No user-facing
behavior. Tracked in ALF-2.

### M1 Identity & Sign-in

The account itself. Sign-up, sign-in, sign-out, sessions, an account page,
TOTP two-factor with recovery codes, lockout after repeated failures, and an
audit log of sign-in events.

- Increment 1: everything above for a single user acting alone. Brief:
  `docs/product/increment-1.md`.
- Later M1 increments (not yet briefed): email verification and password reset
  once outbound email exists, change email, change password, session list with
  remote sign-out, account deletion, passkeys.

### M2 Admin & Orgs

Organizations as the unit of administration. An admin creates an organization,
invites or creates users, puts them in groups, assigns roles, can require
two-factor for everyone in the organization, and reads an organization-wide
audit log. The sign-in audit log from M1 becomes the first feed of that log.

### M3 OIDC provider ("Sign in with Alfulk")

Alfulk acts as a standards-compliant OpenID Connect provider. Developers
register an application, users consent to share profile claims, and the
application receives ID and access tokens. Organizations can restrict which
applications their members may use.

### M4 Drive

Files and folders per user: upload, download, folders, trash with restore,
sharing with other Alfulk users and by link, and per-user and per-organization
quotas.

### M5 Mail

Internal mail between Alfulk users first: a mailbox per account, compose, send,
receive, read, reply, and basic folders. Interoperation with external SMTP and
IMAP comes after internal mail is solid.

## Out of scope for now

These are explicitly not planned for the current roadmap. They may be revisited
after M5, or earlier if the operator asks.

- **External identity federation.** Signing in to Alfulk with Google, Microsoft,
  GitHub, SAML, or LDAP. Alfulk is the identity provider, not a consumer of
  others.
- **Native mobile or desktop apps.** Web only. Pages must be usable on a phone
  browser, but no app-store clients.
- **Calendar, Contacts, Docs, Meet, Photos, or any other Google-suite product**
  beyond Drive and Mail.
- **Real-time collaborative editing** of files in Drive.
- **External mail delivery** (SMTP out, IMAP/POP in, DKIM, SPF) until M5's
  internal mail is complete.
- **Multi-tenant SaaS hosting** of many unrelated customers on one install.
  One deployment serves one operator and the organizations they create.
- **Billing, plans, or payments.**
- **Passkeys / WebAuthn, hardware keys, SMS, or push-based second factors.**
  Increment 1 ships TOTP and recovery codes only.
- **Password reset and email verification** in increment 1. Both require
  outbound email, which does not exist until the operator provides an SMTP
  relay or M5 ships. They are the first candidates for M1 increment 2.
- **An admin UI** of any kind before M2. Increment 1 has no admin; operators
  use database access or management commands.
- **Public API or API keys** before M3.
- **Internationalization.** English only until a module needs otherwise.
- **Importing data** from Google Takeout or other providers.

## How we work

- The Product Manager writes a brief per increment with expected behavior, edge
  cases, and numbered acceptance criteria. The user confirms the brief.
- The CTO turns the acceptance criteria into engineering tasks, each with its
  own branch and pull request linking its issue.
- QA verifies each acceptance criterion on staging with synthetic data. Nothing
  is released to production until every criterion in the increment passes.
- Release notes for each production release are drafted by the Product Manager
  and attached to the production approval.
