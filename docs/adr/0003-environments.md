# ADR-0003: Environments — preview, staging, production

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** CTO
- **Supersedes:** —

## Context

The increment 1 brief requires that every acceptance criterion is checkable on
**staging with synthetic data**. That single sentence settles most of this
decision: staging must be a real, persistent, reachable deployment that behaves
like production, and it must never contain real user data.

Alfulk is an identity platform. Its database holds password hashes, TOTP
secrets, recovery-code hashes and sign-in audit trails. The usual shortcut —
copying a production snapshot into staging so testers have realistic data — is
not available to us. Copying that table is copying the credentials of every
user.

We also want reviewers to click through a change before approving it, which
means per-pull-request preview deployments.

## Decision

Three environment classes. Configuration comes from the environment, never
from committed files — one application image, four settings modules that
differ only in posture, and all variation in environment variables.

### Preview

- **One per open pull request**, created when CI passes on the branch and
  destroyed when the pull request merges or closes.
- Runs on the shared preview host as a Docker Compose stack, reachable at
  `pr-<number>.preview.<domain>`.
- **Its own disposable PostgreSQL database**, seeded from the synthetic
  fixture (below) on every deploy. Data is thrown away with the environment.
- `DEBUG=False` — previews must reproduce production error handling, not hide
  behind the debug page.
- **Not publicly indexable and not publicly linked:** HTTP basic auth at the
  reverse proxy, plus `X-Robots-Tag: noindex`.
- Outbound email is captured, never delivered. In increment 1 that means a
  console or file-based mail backend; a local MailHog-style catcher once M1
  sends real mail.
- Secrets are preview-only values, generated per environment. No production or
  staging secret is ever present on the preview host.

### Staging

- **Persistent and always on**, at `staging.<domain>`. This is where the
  Product Manager's acceptance criteria get verified, so it must be stable and
  predictable, not rebuilt under a tester mid-session.
- **Deployed automatically on every merge to `main`.** If `main` is broken,
  staging is broken, and we find out immediately rather than at release time.
- Same image, same migration path, same reverse proxy and TLS configuration as
  production, on smaller hardware. Differences from production are limited to
  host size, secrets, and the mail destination; anything else is a defect in
  the deployment, because a staging that differs from production stops being
  evidence about production.
- **Synthetic data only** — see below.
- Outbound email goes to a catcher or a sandboxed provider address. Staging
  must never be able to send mail to a real person's inbox.
- Access-restricted at the proxy. Staging contains no real data, but an
  internet-facing sign-in page with known test credentials is an unnecessary
  invitation.

### Production

- `app.<domain>` (exact hostname settled with the domain decision in
  [ADR-0002](0002-hosting-provider.md)).
- **Deployed only from `main`, only from a commit that already passed CI and
  already deployed to staging.** Deployment is triggered manually and gated by
  a GitHub Environment protection rule requiring human approval — see
  [ADR-0004](0004-ci-cd-and-branching.md).
- Separate application and database hosts on a private network. The database
  has no public interface.
- `DEBUG=False`, HSTS, secure cookie flags, `ALLOWED_HOSTS` pinned to the real
  hostname, and `manage.py check --deploy` enforced in CI against the
  production settings module.
- Nightly encrypted database backups to object storage, with a restore drill
  that is executed and documented before the first real user account exists.

### Synthetic data

A single committed fixture plus a management command (`seed_demo_data`) is the
only way preview and staging get populated. One source, used by both, so a
tester's staging account and a reviewer's preview account behave the same.

It contains deterministic, obviously-fake users — known passwords, known TOTP
secrets, a locked-out account, an account with two-factor enabled and one
without — so the increment 1 acceptance criteria can be walked through without
anyone inventing test data by hand.

**Production data is never copied into any other environment.** There is no
approval process for this and no exception; it is not a policy that can be
waived, because the data in question is credentials. If a production bug needs
reproducing, it is reproduced with synthetic data that has the same shape.

### Configuration and secrets

- Settings split into `config/settings/{base,local,test,production}.py`.
  Staging and preview both use the `production` module and differ only by
  environment variables. This is deliberate: a staging-specific settings module
  is how staging quietly stops resembling production.
- All deployment configuration comes from environment variables, read through
  `django-environ`. `.env.example` documents every variable; real `.env` files
  are never committed.
- Secrets live in GitHub Environments (`preview`, `staging`, `production`) for
  deployment, and in a root-owned `EnvironmentFile` on each host at runtime.
- **Every environment has independently generated secrets.** `SECRET_KEY`,
  `RECOVERY_CODE_HMAC_KEY` and database credentials are never shared between
  environments — a preview-host compromise must not reach staging, and staging
  must not reach production.
- Rotating `RECOVERY_CODE_HMAC_KEY` invalidates every outstanding recovery
  code in that environment. Operator documentation must say so plainly.

## Alternatives considered

- **No preview environments; review from the diff and CI alone.** Rejected:
  increment 1 is almost entirely user-facing flows, and a reviewer cannot
  assess a sign-in flow by reading a template.
- **A VM per preview environment.** Cleaner isolation, unpredictable cost, and
  needs a provisioning layer we do not have. Revisit if the shared host becomes
  a bottleneck.
- **Anonymised production dumps for staging.** Rejected. Anonymisation that
  preserves useful shape repeatedly turns out to be reversible, and for
  credential material the only safe transformation destroys the value anyway.
- **Two environments only (staging doubles as preview).** Rejected: concurrent
  pull requests would fight over one deployment, and the Product Manager's
  acceptance testing would be disrupted by every unmerged branch.
- **A separate `staging` settings module.** Rejected: it is exactly the
  mechanism by which staging drifts away from production and stops being
  evidence.

## Consequences

- Three deployment targets to build and maintain, which is real work in M0.
  The preview lifecycle (create on CI pass, destroy on close) is the fiddliest
  part and should be scoped as its own task.
- Acceptance testing is only as good as the synthetic fixture. The fixture is a
  product artifact, not test scaffolding, and needs updating as each module
  lands.
- Reproducing a production-only bug is harder without production data. We
  accept that cost; for an identity platform it is the right trade.
- Four parallel sets of secrets to generate, store and rotate. Rotation
  procedure needs documenting as part of the deployment task.
- Staging breaks whenever `main` breaks. That is intended — it makes `main`
  breakage visible — but it means a broken `main` blocks acceptance testing and
  must be treated as urgent.
