from unittest import mock

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse


class HealthzTests(TestCase):
    def test_reports_ok_when_the_database_is_reachable(self):
        response = self.client.get(reverse("core:healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_reports_503_when_the_database_is_unreachable(self):
        # Patching the view's own reference leaves the request's transaction
        # machinery working, so this exercises the probe rather than breaking
        # the whole request.
        with mock.patch("alfulk.core.views.connection") as unreachable:
            unreachable.cursor.side_effect = OperationalError("database is down")

            response = self.client.get(reverse("core:healthz"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unhealthy", "database": "unreachable"})


class HomeTests(TestCase):
    def test_renders(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
