"""Developer-machine settings. Never used for a deployed environment."""

import os

# A throwaway key so `manage.py runserver` works from a fresh clone. Deployed
# environments supply real values and base.py would otherwise refuse to start.
os.environ.setdefault("SECRET_KEY", "django-insecure-local-development-only")
os.environ.setdefault("RECOVERY_CODE_HMAC_KEY", "local-development-only")

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# The template reference page at /_ui/forms. Always on locally: it is the
# fastest way to see what a change to the shared partials did.
UI_REFERENCE_ENABLED = True

# Cheaper Argon2 so local test runs and fixtures are not dominated by hashing.
# Production values stay in base.py.
ARGON2_TIME_COST = 1
ARGON2_MEMORY_COST = 8192
ARGON2_PARALLELISM = 1
