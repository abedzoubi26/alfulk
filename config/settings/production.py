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

# Ramp max-age per hostname (300 -> a day -> a year) rather than starting at a
# year: a TLS misconfiguration on a hostname's first deploy would otherwise lock
# visitors out for twelve months. The long value is set per environment once
# certificate issuance and renewal are proven.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=300)  # noqa: F405

# Both default to False because preview and staging run this same module.
# `preload` is not a per-host assertion -- it applies to the registrable domain
# (eTLD+1) and takes months to undo -- so asserting it from throwaway per-PR
# hosts is how a domain gets onto the preload list by accident. Enable both in
# the production environment only, once preloading is a deliberate decision.
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)  # noqa: F405
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)  # noqa: F405

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
