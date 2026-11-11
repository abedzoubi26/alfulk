"""Settings shared by every environment.

Environment-specific modules (``local``, ``test``, ``production``) import from
here and override only what genuinely differs. Staging and preview both run the
``production`` module and differ from production only by environment variables
-- see ADR-0003.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# Read a local .env when present. Deployed environments inject real environment
# variables instead and have no .env file.
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    env.read_env(str(_env_file))

# --- Core -------------------------------------------------------------------

SECRET_KEY = env("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Applications -----------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS: list[str] = []

LOCAL_APPS = [
    "alfulk.accounts",
    "alfulk.core",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --- Database ---------------------------------------------------------------

DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgres://alfulk:alfulk@localhost:5432/alfulk",
    )
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# --- Templates --------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Authentication ---------------------------------------------------------

# Set before the first migration that touches `auth`. Changing it later means
# migrating every table that points at the user.
AUTH_USER_MODEL = "accounts.User"

# auth.E003 insists the USERNAME_FIELD carries a plain unique index. Ours is
# unique on LOWER(email), which is strictly stronger: it rejects every row a
# case-sensitive index would, plus the case variants. Django's check cannot
# read an expression constraint, so silence it rather than satisfy it with a
# second, redundant index -- that index would also tell the next reader that
# letter case is part of identity, which is the thing we are ruling out. The
# constraint is covered by alfulk/accounts/tests/test_email_uniqueness.py.
SILENCED_SYSTEM_CHECKS = ["auth.E003"]

# --- Passwords --------------------------------------------------------------

# Argon2id parameters, read by alfulk.core.hashers.AlfulkArgon2PasswordHasher.
# Django's stock Argon2PasswordHasher hard-codes these as class attributes, so
# pinning them here means tuning is a reviewable change rather than whatever
# argon2-cffi happens to default to this release (ADR-0001).
ARGON2_TIME_COST = env.int("ARGON2_TIME_COST", default=3)
ARGON2_MEMORY_COST = env.int("ARGON2_MEMORY_COST", default=65536)  # 64 MiB
ARGON2_PARALLELISM = env.int("ARGON2_PARALLELISM", default=4)

# Argon2id first, so Django transparently upgrades any weaker hash it finds on
# the next successful sign-in.
PASSWORD_HASHERS = [
    "alfulk.core.hashers.AlfulkArgon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Keyed hash for one-time recovery codes. Separate from SECRET_KEY so that
# rotating one does not silently invalidate the other. Rotating this key
# invalidates every outstanding recovery code -- see ADR-0001.
RECOVERY_CODE_HMAC_KEY = env("RECOVERY_CODE_HMAC_KEY")

# --- Sessions ---------------------------------------------------------------

# Database-backed so an administrator can revoke a session; M2 requires that,
# and cookie-only sessions cannot offer it.
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = "alfulk_sessionid"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=60 * 60 * 12)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # makes SESSION_COOKIE_AGE an idle timeout

CSRF_COOKIE_HTTPONLY = False  # the template tag reads it; the value is per-session
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

X_FRAME_OPTIONS = "DENY"

# --- Internationalisation ---------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static files -----------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --- Email ------------------------------------------------------------------

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@localhost")

# --- Logging ----------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
