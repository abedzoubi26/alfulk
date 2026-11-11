"""The template reference page: the partials assembled into a real request."""

from django.test import TestCase, override_settings
from django.urls import reverse


class ReferencePageDisabledTests(TestCase):
    @override_settings(UI_REFERENCE_ENABLED=False)
    def test_is_not_served_where_it_is_switched_off(self):
        response = self.client.get(reverse("core:ui_reference"))

        self.assertEqual(response.status_code, 404)


@override_settings(UI_REFERENCE_ENABLED=True)
class ReferencePageTests(TestCase):
    url = reverse("core:ui_reference")

    def test_renders_an_empty_form_with_no_error_summary(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/ui_reference.html")
        self.assertContains(response, 'for="id_email"')
        self.assertNotContains(response, "There is a problem")

    def test_form_is_a_csrf_protected_post(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'method="post"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_error_state_shows_field_errors_and_a_form_level_error(self):
        response = self.client.get(self.url, {"state": "errors"})
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('role="alert"', html)
        self.assertIn("There is a problem", html)
        # The form-level error, which belongs to no field.
        self.assertIn("Incorrect email or password.", html)
        # And a field error, attached to the field that caused it.
        self.assertIn('id="id_email_error"', html)
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('href="#id_email"', html)

    def test_no_template_source_reaches_the_browser(self):
        # Covers every partial at once, including the error-state branches.
        html = self.client.get(self.url, {"state": "errors"}).content.decode()

        self.assertNotIn("{#", html)
        self.assertNotIn("{%", html)

    def test_invalid_submission_comes_back_with_every_error_at_once(self):
        response = self.client.post(
            self.url,
            {"email": "nope", "display_name": "", "password": "short"},
        )
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="id_email_error"', html)
        self.assertIn('id="id_display_name_error"', html)
        self.assertIn('id="id_password_error"', html)
        self.assertIn('id="id_accepted_error"', html)

    def test_valid_submission_redirects_and_reports_success(self):
        response = self.client.post(
            self.url,
            {
                "email": "ada@example.com",
                "display_name": "Ada",
                "password": "a-long-enough-password",
                "contact_preference": "email",
                "accepted": "on",
            },
            follow=True,
        )

        self.assertRedirects(response, self.url)
        self.assertContains(response, "That submission was valid. Nothing was saved.")
        self.assertContains(response, 'role="status"')
