from django.test import TestCase
from django.urls import reverse


class HealthzTests(TestCase):
    def test_reports_ok_when_the_database_is_reachable(self):
        response = self.client.get(reverse("core:healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})


class HomeTests(TestCase):
    def test_renders(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
