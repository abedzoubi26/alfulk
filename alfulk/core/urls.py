from django.urls import path

from alfulk.core import ui_reference, views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("healthz", views.healthz, name="healthz"),
    # Registered in every environment but served only where
    # UI_REFERENCE_ENABLED is set; the view 404s otherwise. Registering it
    # unconditionally keeps `reverse()` working, so the "it is off" behaviour
    # is a plain test rather than a URLconf reload.
    path("_ui/forms", ui_reference.reference_page, name="ui_reference"),
]
