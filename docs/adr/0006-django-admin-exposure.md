# ADR-0006: Where the Django admin lives, and whether production serves it

- **Status:** Proposed
- **Date:** 2026-11-11
- **Deciders:** CTO
- **Supersedes:** —

## Context

The foundation mounted `django.contrib.admin` at Django's default `/admin/`.
The Code Reviewer flagged that on PR #2 as something to fix before there was
anything behind it, and that moment is now: M1 puts real accounts, TOTP
secrets and recovery-code hashes behind that login form.

Three things make this more than a cosmetic change.

**The default path is the first thing anyone tries.** Moving it does not make
the admin secure — anyone who can enumerate URLs or read a stack trace will
find it. What it does is remove the standing volume of untargeted credential
stuffing against a form that, by design, grants total access to the user
table. That is a real reduction in noise and in the chance of a lucky guess,
and it costs one environment variable. It is not a substitute for
authentication, and this record should not be read as claiming otherwise.

**Django's admin has its own login form, and it does not know about our second
factor.** M1's entire point is that an Alfulk account needs a password and a
TOTP code. An admin login that takes a password alone would be a documented
bypass of the control we are building, sitting at a known URL, for the
accounts with the most authority.

**M2 replaces it anyway.** "Admin & Orgs" brings a purpose-built admin surface
with roles and an audit trail. The Django admin is scaffolding we need for
development and for acceptance testing on staging; it is not the thing we
intend operators to use against real accounts.

[ADR-0003](0003-environments.md) already settles the mechanism: preview,
staging and production run one image and one settings module, and differ only
by environment variables. So the mount path has to be configuration, not a
per-environment code difference.

## Decision

### 1. The mount path comes from the environment

`ADMIN_URL` gives the prefix the admin is mounted at, normalised in
`config/settings/base.py` so that `ops-9f2c1b74`, `/ops-9f2c1b74` and
`ops-9f2c1b74/` all mean the same thing.

- `config/settings/base.py` defaults it to `admin/`, which is for developer
  machines only. Local is not internet-facing and a familiar path is worth
  more there than obscurity is.
- `config/settings/production.py` gives it **no default**. Preview, staging
  and production all use that module, so each one must state its own value or
  fail at startup — the same treatment `ALLOWED_HOSTS` already gets, and for
  the same reason.
- Each environment's value is independent, like every other secret-ish value
  under ADR-0003. A preview host's path must not reveal production's.

### 2. An empty value means the admin is not routed

`ADMIN_URL=""` leaves `django.contrib.admin` installed — management commands
and its template machinery still work — but adds no URL pattern for it. There
is no admin to find, at any path, in that environment.

This is what makes the question in section 4 a configuration change rather
than a code change.

### 3. `manage.py check --deploy` fails on the default path

A new check, `alfulk.E001`, errors when a deployed environment still has
`ADMIN_URL == "admin/"`. CI runs `check --deploy --fail-level WARNING`
against the production settings module on every pull request
([ADR-0004](0004-ci-cd-and-branching.md)), so this is enforced rather than
remembered. The check is `deploy=True`, so it stays quiet on developer
machines.

### 4. Whether production serves the admin in M1 — **open, for the CTO**

The mechanism above supports either answer, and the answer is an environment
variable. The recommendation this record proposes, for the CTO to accept or
override:

> **In M1, production sets `ADMIN_URL=""` and does not route the Django
> admin. Staging and preview route it at their own paths.**

The case for it: until section 5 lands, the Django admin is a password-only
route to every account on the platform, and M1's whole claim is that no such
route exists. Staging is where acceptance testing happens and it holds only
synthetic data, so nothing in increment 1 needs the admin in production.

The cost of it, stated plainly so the decision is informed: production
operator work in M1 — resetting an account, inspecting a user, clearing a
lockout — happens through `manage.py` on the application host, not through a
browser. That is slower, it is harder to do accidentally, and it leaves a
shell-history trail rather than an application audit record. If the CTO
judges that cost too high, the alternative is to route the admin in production
and accept section 5 as a blocking prerequisite instead of a follow-on.

Either answer affects M2's scope: if production has no Django admin through
M1, then M2's admin surface is the first production admin tooling that exists,
and the operator tasks above are part of its brief rather than nice-to-haves.

### 5. Once two-factor exists, the admin must require it

When E8 (TOTP enrolment) and E11 (second-factor sign-in) land, the Django
admin must not be reachable through `django.contrib.admin`'s own
password-only login. The admin site is to be configured so that
authentication goes through Alfulk's sign-in flow, including the second
factor, and so that staff access requires a session that has completed it.

This is a requirement on whoever lands E11, recorded here because it is the
part of this decision that would otherwise be quietly dropped: an admin login
that bypasses TOTP defeats the control M1 exists to add.

## Alternatives considered

- **Leave it at `/admin/` and rely on authentication alone.** Defensible in
  general, and we are not pretending the move is a security control. Rejected
  because the cost here is one environment variable, and because the asset
  behind this particular form is the credential store of every user.
- **Restrict the admin by IP allowlist at the reverse proxy instead.** A
  stronger control than a path, and worth having later. Rejected as the
  mechanism for now because we do not yet have a stable operator network
  range, and because it lives in deployment configuration that ADR-0002 has
  not settled. It composes with this decision rather than replacing it.
- **Remove `django.contrib.admin` from `INSTALLED_APPS` entirely.** Cleanest
  possible answer to "can production serve the admin", and rejected because it
  makes the posture a code change per environment, which is exactly what
  ADR-0003 forbids. Unrouting it achieves the same thing as configuration.
- **A random path generated at deploy time.** Rejected: an operator who cannot
  predict the URL cannot use it in an incident, and it would end up written
  down somewhere worse than an environment variable.

## Consequences

- Every deployed environment gains a required variable. A deploy that forgets
  `ADMIN_URL` fails at startup rather than serving `/admin/` — intended, and
  it must be in the deployment runbook before the first deploy.
- The admin path is operational knowledge an operator needs to hand. It
  belongs with the environment's other configuration, not in the repository.
- Bookmarks and any documentation pointing at `/admin/` break. There are none
  today, which is why this is being done now.
- If the CTO accepts section 4's recommendation, M1 production operator tasks
  run through `manage.py`, and M2's admin surface inherits them as scope.
- Section 5 is a prerequisite on E11 that this record does not itself deliver.
