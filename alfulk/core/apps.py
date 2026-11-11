from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "alfulk.core"
    verbose_name = "Core"

    def ready(self):
        # Importing for the side effect of registering the deploy checks.
        from alfulk.core import checks  # noqa: F401
