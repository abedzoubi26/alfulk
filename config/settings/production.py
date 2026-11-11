"""Settings for every deployed environment.

Preview, staging and production all use this module. They differ only in
environment variables, which is what keeps staging a usable prediction of
production -- see ADR-0003.
"""

from .base import *  # noqa: F403

DEBUG = False

# No default: a deployment that forgets ALLOWED_HOSTS should fail loudly at
# startup rather than quietly serve every Host header.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405

# --- Transport security -----------------------------------------------------

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
