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
# With SESSION_SAVE_EVERY_REQUEST below, this is the *idle* timeout, not the
# absolute lifetime: the brief asks for 30 minutes idle. The 12-hour absolute
# lifetime is a separate mechanism and arrives with E5.
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=60 * 30)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # makes SESSION_COOKIE_AGE an idle timeout

CSRF_COOKIE_HTTPONLY = False  # the template tag reads it; the value is per-session
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

X_FRAME_OPTIONS = "DENY"

# --- Django admin -----------------------------------------------------------


def normalise_admin_url(value: str) -> str:
    """Canonicalise an admin mount prefix: no leading slash, one trailing one.

    An empty value means the admin is not routed in this environment at all.
    """
    value = value.strip().strip("/")
    return f"{value}/" if value else ""


# Where `django.contrib.admin` is mounted, or "" to not route it at all.
#
# An environment variable rather than a constant because ADR-0003 requires
# environments to differ only by configuration, and because the admin of an
# identity platform should not sit at the one URL every scanner tries first.
# That last part is obscurity, not security -- it thins drive-by traffic
# against the login form and nothing more -- so it stacks with authentication
# rather than standing in for it. See ADR-0006.
#
# `production` overrides this with a value that has no default, so a deployed
# environment has to choose. The default here is only for developer machines.
ADMIN_URL = normalise_admin_url(env("ADMIN_URL", default="admin/"))

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
