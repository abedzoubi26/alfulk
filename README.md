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

Requires Python 3.12+ and Docker (for PostgreSQL).

```bash
cp .env.example .env            # then edit SECRET_KEY and RECOVERY_CODE_HMAC_KEY
docker compose up -d db         # PostgreSQL on localhost:5432
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

The app is then at http://localhost:8000 and its health endpoint at
http://localhost:8000/healthz.

The Django admin is mounted wherever `ADMIN_URL` says — `admin/` by default
locally, a path of its own in each deployed environment, and nowhere at all
when the variable is empty. See [ADR-0006](docs/adr/0006-django-admin-exposure.md).

### Checks

Run these before opening a pull request; CI runs the same set.

```bash
ruff check .
ruff format --check .
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Contributing

Every task gets its own branch and a pull request linking its Paperclip issue.
CI must pass and the Code Reviewer must approve before the change is merged
into `main`. Branch naming, required checks and the deployment path are
specified in [ADR-0004](docs/adr/0004-ci-cd-and-branching.md).
