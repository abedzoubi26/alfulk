"""Project-specific deployment checks, run by `manage.py check --deploy`.

CI runs that command against the production settings module at
`--fail-level WARNING` (ADR-0004), so anything registered here is enforced on
every pull request rather than left to review.
"""

from django.conf import settings
from django.core.checks import Error, Tags, register

DEFAULT_ADMIN_URL = "admin/"


@register(Tags.security, deploy=True)
def admin_url_is_not_the_django_default(app_configs, **kwargs):
    """A deployed environment must not serve the admin from /admin/.

    Deploy-only: a developer machine keeping the familiar path is fine, and
    failing `manage.py check` there would be noise.
    """
    if settings.ADMIN_URL != DEFAULT_ADMIN_URL:
        return []

    return [
        Error(
            "ADMIN_URL is still Django's default 'admin/'.",
            hint=(
                "Set the ADMIN_URL environment variable to a path unique to "
                "this environment, or to the empty string to not route the "
                "Django admin here at all. See ADR-0006."
            ),
            id="alfulk.E001",
        )
    ]
