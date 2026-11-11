"""Settings for the automated test suite, locally and in CI."""

import os

os.environ.setdefault("SECRET_KEY", "django-insecure-test-only")
os.environ.setdefault("RECOVERY_CODE_HMAC_KEY", "test-only-recovery-key")

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Argon2id is kept -- the hashing path is part of what we are testing -- but at
# the cheapest parameters that still exercise it. Swapping in MD5 here would
# mean the test suite never runs the hasher that production uses.
ARGON2_TIME_COST = 1
ARGON2_MEMORY_COST = 8192
ARGON2_PARALLELISM = 1

# Static file hashing needs a manifest built by collectstatic, which tests do
# not run.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# WhiteNoise serves nothing under test and warns on every request that
# STATIC_ROOT has not been collected. Dropping it keeps the suite's output
# free of a warning that would train us to ignore warnings.
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405
