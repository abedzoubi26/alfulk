from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = []

# Mounted at a path the environment chooses, and not mounted at all when
# ADMIN_URL is empty -- an environment can decline to expose the Django admin
# rather than hide it. See ADR-0006.
if settings.ADMIN_URL:
    urlpatterns.append(path(settings.ADMIN_URL, admin.site.urls))

urlpatterns.append(path("", include("alfulk.core.urls")))
