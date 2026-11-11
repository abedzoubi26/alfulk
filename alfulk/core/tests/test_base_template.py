"""The page skeleton every screen inherits."""

from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.urls import reverse

from alfulk.core import views


class BaseLayoutTests(TestCase):
    def test_declares_a_language(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, '<html lang="en">')

    def test_first_focusable_element_skips_to_the_main_landmark(self):
        response = self.client.get(reverse("core:home"))
        html = response.content.decode()

        self.assertIn('<a class="skip-link" href="#main-content">', html)
        self.assertIn('id="main-content"', html)
        # Nothing focusable may come before it, or the skip link is useless.
        self.assertLess(html.index("skip-link"), html.index('class="brand"'))

    def test_no_template_source_reaches_the_browser(self):
        # A `{# ... #}` comment spanning more than one line is not a comment in
        # Django -- it is rendered verbatim. Cheap to check, invisible to spot.
        html = self.client.get(reverse("core:home")).content.decode()

        self.assertNotIn("{#", html)
        self.assertNotIn("{%", html)

    def test_main_landmark_can_receive_focus(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, '<main class="site-main" id="main-content" tabindex="-1">')


class MessageRegionTests(TestCase):
    """Flash messages are a live region, and inside the landmark the skip link
    targets -- otherwise skipping the header skips the notification too."""

    def render_home_with_a_message(self, level: int, text: str) -> str:
        request = RequestFactory().get(reverse("core:home"))
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        messages.add_message(request, level, text)

        return views.home(request).content.decode()

    def test_message_is_announced_politely(self):
        html = self.render_home_with_a_message(messages.SUCCESS, "You have been signed out.")

        self.assertIn('<div class="messages" role="status" aria-live="polite">', html)
        self.assertIn("You have been signed out.", html)
        self.assertIn("message--success", html)

    def test_message_sits_inside_the_main_landmark(self):
        html = self.render_home_with_a_message(messages.ERROR, "Something went wrong.")

        self.assertLess(html.index('id="main-content"'), html.index('class="messages"'))
        self.assertIn("message--error", html)

    def test_no_region_is_rendered_when_there_is_nothing_to_say(self):
        response = self.client.get(reverse("core:home"))

        self.assertNotContains(response, 'class="messages"')
