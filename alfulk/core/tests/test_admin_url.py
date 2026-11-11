import importlib

from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, clear_url_caches, reverse

import config.urls
from alfulk.core.checks import admin_url_is_not_the_django_default
from config.settings.base import normalise_admin_url

# Shaped like a real deployment's value: not guessable, not a word.
MOVED_ADMIN_URL = "ops-9f2c1b74/"


class NormaliseAdminUrlTests(TestCase):
    def test_accepts_the_shapes_an_operator_is_likely_to_type(self):
        for given in ("ops-9f2c1b74", "/ops-9f2c1b74", "ops-9f2c1b74/", "  /ops-9f2c1b74/  "):
            with self.subTest(given=given):
                self.assertEqual(normalise_admin_url(given), MOVED_ADMIN_URL)

    def test_keeps_a_nested_path_intact(self):
        self.assertEqual(normalise_admin_url("/internal/ops-9f2c1b74"), "internal/ops-9f2c1b74/")

    def test_empty_stays_empty(self):
        for given in ("", "   ", "/"):
            with self.subTest(given=given):
                self.assertEqual(normalise_admin_url(given), "")


class AdminMountTests(TestCase):
    """The admin is routed where ADMIN_URL says, and nowhere else.

    `config.urls` reads ADMIN_URL once at import, so each test reloads the
    URLconf under its own override and puts it back afterwards.
    """

    def mount_admin_at(self, admin_url):
        override = override_settings(ADMIN_URL=admin_url)
        override.enable()
        self.addCleanup(self.restore, override)
        self.reload_urlconf()

    def restore(self, override):
        override.disable()
        self.reload_urlconf()

    def reload_urlconf(self):
        importlib.reload(config.urls)
        clear_url_caches()

    def test_admin_is_served_from_the_configured_path(self):
        self.mount_admin_at(MOVED_ADMIN_URL)

        response = self.client.get(f"/{MOVED_ADMIN_URL}")

        # Unauthenticated, so the admin bounces to its own login page -- which
        # is enough to prove the site is mounted there.
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(f"/{MOVED_ADMIN_URL}login/"))
        self.assertEqual(reverse("admin:index"), f"/{MOVED_ADMIN_URL}")

    def test_the_default_path_is_a_404_once_the_admin_has_moved(self):
        self.mount_admin_at(MOVED_ADMIN_URL)

        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_an_empty_admin_url_routes_no_admin_at_all(self):
        self.mount_admin_at("")

        self.assertEqual(self.client.get("/admin/").status_code, 404)
        self.assertEqual(self.client.get(f"/{MOVED_ADMIN_URL}").status_code, 404)
        with self.assertRaises(NoReverseMatch):
            reverse("admin:index")

    def test_the_rest_of_the_site_still_routes_with_no_admin_mounted(self):
        self.mount_admin_at("")

        self.assertEqual(self.client.get("/healthz").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 200)


class AdminUrlDeployCheckTests(TestCase):
    @override_settings(ADMIN_URL="admin/")
    def test_errors_when_a_deployment_leaves_the_admin_at_the_django_default(self):
        errors = admin_url_is_not_the_django_default(app_configs=None)

        self.assertEqual([error.id for error in errors], ["alfulk.E001"])

    @override_settings(ADMIN_URL=MOVED_ADMIN_URL)
    def test_passes_once_the_admin_has_been_moved(self):
        self.assertEqual(admin_url_is_not_the_django_default(app_configs=None), [])

    @override_settings(ADMIN_URL="")
    def test_passes_when_the_admin_is_not_routed_at_all(self):
        self.assertEqual(admin_url_is_not_the_django_default(app_configs=None), [])
