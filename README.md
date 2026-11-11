# Alfulk

A self-hosted replacement for Google's account platform: one identity for
sign-in, profiles and organizations, plus Drive (files) and Mail.

## Status

Early development — **M0 Foundations**. Nothing here is usable yet.

## Roadmap

| Module | Scope |
| --- | --- |
| **M0** | Foundations: repository, CI/CD, environments, deployment |
| **M1** | Identity & Sign-in: sign-up, sign-in, sessions, TOTP two-factor, recovery codes, lockout, sign-in audit log |
| **M2** | Admin & Orgs: organizations, admin user management, roles, audit log |
| **M3** | "Sign in with Alfulk": OIDC provider |
| **M4** | Drive: upload, folders, trash, sharing, quotas |
| **M5** | Mail: internal mail between Alfulk users first |

## Stack

Python 3.12+, Django 5.2 LTS with server-rendered templates, PostgreSQL 16,
Argon2id password hashing, TOTP two-factor. See
[ADR-0001](docs/adr/0001-technology-stack.md) for the reasoning.

## Documentation

- [Architecture decisions](docs/adr/) — the stack, hosting, environments and CI/CD
- [Product plan and increment briefs](docs/product/) — owned by the Product Manager

## Local development

Requires [uv](https://docs.astral.sh/uv/) and Docker (for PostgreSQL). uv
fetches the Python interpreter itself — the version in `.python-version` — so
a separate Python install is not needed.

```bash
cp .env.example .env            # then edit SECRET_KEY and RECOVERY_CODE_HMAC_KEY
docker compose up -d db         # PostgreSQL on localhost:5432
uv sync --extra dev --locked    # creates .venv from uv.lock, exactly
uv run python manage.py migrate
uv run python manage.py runserver
```

The app is then at http://localhost:8000 and its health endpoint at
http://localhost:8000/healthz.

`--locked` is the point: it installs what `uv.lock` records and fails rather
than re-resolving, so your machine, CI and the deployed image run the same
versions down to the transitive graph. Drop it only when you are deliberately
changing dependencies.

### Checks

Run these before opening a pull request; CI runs the same set.

```bash
uv run ruff check .
uv run ruff format --check .
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test
uv run pip-audit --skip-editable
```

## Dependencies

`pyproject.toml` declares the version ranges we accept. `uv.lock` pins the
full transitive graph to exact versions with SHA-256 hashes, and is
committed. The two are reviewed together: a change to one without the other
fails the `Lockfile up to date` job in CI.

```bash
# Add or remove a dependency
uv add 'some-package>=1.2'          # --optional dev for a dev-only tool
uv remove some-package

# Upgrade one package within the range pyproject.toml already allows
uv lock --upgrade-package django

# Upgrade everything within the declared ranges
uv lock --upgrade

# Widen or change a range: edit pyproject.toml, then
uv lock
```

Each of these rewrites `uv.lock`. Commit the manifest and the lock in the
same commit, then run `uv sync --extra dev --locked` to bring your
environment in line and run the checks above — `pip-audit` reads the
installed environment, so it reports on the locked versions rather than on
whatever the ranges happen to permit today.

If a consumer needs a plain pip-installable artefact, export one from the
lock rather than hand-maintaining a second list:

```bash
uv export --format requirements-txt --no-emit-project --extra dev
```

## Contributing

Every task gets its own branch and a pull request linking its Paperclip issue.
CI must pass and the Code Reviewer must approve before the change is merged
into `main`. Branch naming, required checks and the deployment path are
specified in [ADR-0004](docs/adr/0004-ci-cd-and-branching.md).
