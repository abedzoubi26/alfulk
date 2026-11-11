# ADR-0004: CI/CD, branching and review gates

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** CTO
- **Supersedes:** —

## Context

Alfulk is written mostly by agents working in parallel on separate tasks. The
board has set the delivery rule: **each task gets its own branch and a pull
request that links its issue; CI must pass and the Code Reviewer must approve;
then the CTO merges into `main`.**

That rule only means anything if it is enforced by the platform rather than by
convention. An agent that can push to `main` eventually will, and a review gate
that depends on everyone remembering it is not a gate.

Increment 1 also raises the stakes on what CI checks. A test suite that passes
while `DEBUG=True` leaks into production settings, or while a model change has
no migration, is not protecting anything.

## Decision

### Branching

- **Trunk-based.** `main` is always deployable. No long-lived development or
  release branches.
- **One branch per task**, named `<type>/<issue-id>-<slug>` — for example
  `feat/alf-7-totp-enrolment`, `fix/alf-12-session-rotation`. Types: `feat`,
  `fix`, `chore`, `docs`, `refactor`.
- **Short-lived branches.** A branch open for more than a few days is a
  signal that the task was scoped too large.
- **Pull requests are squash-merged**, giving `main` a linear history of one
  commit per task. Merge commits and rebase-merges are disabled.
- **Every pull request links its Paperclip issue** in the description. The
  pull request template requires it.

### Required CI checks on every pull request

All of these must pass before merge, enforced as required status checks:

| Check | What it catches |
| --- | --- |
| `ruff check` | Lint violations, unused imports, likely bugs |
| `ruff format --check` | Formatting drift — formatting is never a review topic |
| `manage.py makemigrations --check --dry-run` | **A model changed without a migration.** The single most common way a Django branch breaks `main` |
| `manage.py test` against real PostgreSQL 16 | Behaviour. Run against PostgreSQL, not SQLite, so database-specific behaviour is actually exercised |
| `coverage report --fail-under` | Untested new code. The floor starts modest and ratchets upward; it is never lowered to make a pull request pass |
| `manage.py check --deploy` with production settings | **Insecure production posture** — `DEBUG=True`, missing HSTS, non-secure cookies. Run at `--fail-level WARNING` |
| `pip-audit` | Known CVEs in dependencies |

`check --deploy` is in the list because it is the one check that tests the
configuration we actually ship rather than the configuration we test under.

### Branch protection on `main`

To be configured by the repository owner — see the deliverables list on the
foundation issue:

- Require a pull request before merging; **no direct pushes, including by
  administrators**.
- Require **one approving review**, from the Code Reviewer / Security Engineer.
- Dismiss stale approvals when new commits are pushed.
- Require all status checks above to pass, and require the branch to be up to
  date with `main`.
- Require conversation resolution before merging.
- Require linear history.
- Block force-pushes and branch deletion.

### Deployment

- **Merge to `main` → deploy to staging automatically.** No gate. Staging
  reflects `main` at all times.
- **Production deploys are manual and human-approved.** The workflow targets
  a GitHub Environment named `production` with a required-reviewer protection
  rule, so the deploy job pauses until a human approves it in the GitHub UI.
  Only a commit already on `main` and already deployed to staging is eligible.
- **The artifact is a container image** built once per commit, tagged with the
  commit SHA, pushed to GitHub Container Registry. **Staging and production
  deploy the same image by digest** — the thing tested on staging is byte-for-byte
  the thing that reaches production. Nothing is rebuilt at deploy time.
- **Migrations run as a separate step before the new image serves traffic**,
  and must be backward-compatible with the currently running version so a
  rollback does not strand the database ahead of the code.
- **Rollback is redeploying the previous image digest.** Because migrations
  are backward-compatible, this needs no database action. Any migration that
  cannot be made backward-compatible is split into expand/contract steps
  across two deployments.

### Secrets in CI

- Deployment credentials live in GitHub Environment secrets, not repository
  secrets, so the `production` environment's SSH key is unavailable to a
  workflow running against `staging`.
- **Workflows triggered by `pull_request` get no secrets and no deploy
  permissions.** Preview deployment runs in a separate, privileged workflow
  keyed off the pull request's head SHA after CI passes, never on untrusted
  pull request code with secrets in scope.
- CI uses only first-party `actions/*` steps, pinned to a major version tag.
  **Any third-party action is pinned to a full commit SHA**, never a tag — a
  tag is mutable and a compromised action runs with our secrets.
- `GITHUB_TOKEN` permissions are set to `contents: read` at the workflow level
  and widened per job only where a job genuinely needs more.

## Alternatives considered

- **GitFlow with `develop` and release branches.** Rejected: merge overhead
  and long-lived divergence for no benefit at this cadence. We ship from
  trunk.
- **Merge commits instead of squash.** Rejected: branch-internal commits from
  parallel agents add noise without adding history anyone reads. One commit
  per task is the useful granularity, and it makes reverting a task trivial.
- **Deploying to production automatically on merge.** Rejected for an
  identity platform at this stage. The cost of a bad deploy is user accounts;
  a human approval click is cheap insurance. Revisit once the test suite and
  monitoring have earned the trust.
- **Building the image at deploy time on the host.** Rejected: the artifact
  tested is then not the artifact deployed, and it puts a build toolchain on
  production hosts.
- **Running CI against SQLite for speed.** Rejected: constraint, transaction
  and locking behaviour differ from PostgreSQL in exactly the places identity
  and quota logic will depend on. A service container costs seconds.
- **No coverage gate.** Rejected, but set as a *ratchet* rather than an
  aspirational number — a floor that gets lowered to land a pull request is
  worse than no floor, because it looks like a gate.

## Consequences

- Nobody, including the CTO, can push to `main`. All changes go through a
  pull request. This is deliberate and should not be relaxed under deadline
  pressure.
- The Code Reviewer is a required participant in every change and therefore a
  potential bottleneck. If review latency becomes the constraint, the answer
  is smaller pull requests, not a weaker gate.
- CI runtime is on the critical path of every task. It needs to stay fast —
  dependency caching, and parallel jobs where the checks are independent.
- The coverage floor will block pull requests that add untested code. That is
  the point, and it needs saying out loud so it is not treated as CI being
  flaky.
- Backward-compatible migrations are a real constraint on how schema changes
  are written. Engineers need to know the expand/contract pattern before the
  first destructive migration, not after.
- Branch protection, GitHub Environments and the registry all need
  **repository-owner** configuration. Agents cannot set these, so they are
  listed as human prerequisites on the foundation issue and block the first
  deployment.
