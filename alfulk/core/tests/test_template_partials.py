"""The accessibility baseline, expressed as tests.

These assertions are the contract E4, E5, E7 and E10 inherit by including the
partials. They are written against a form defined here rather than against a
product form so that a change to sign-up cannot quietly change what the shared
layer is required to do.
"""

from django import forms
from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.html import format_html


class SampleForm(forms.Form):
    email = forms.EmailField(label="Email", help_text="The address you sign in with.")
    display_name = forms.CharField(label="Display name", max_length=80)
    nickname = forms.CharField(label="Nickname", required=False)
    contact_preference = forms.ChoiceField(
        label="How should we contact you?",
        choices=[("email", "By email"), ("none", "Do not contact me")],
        widget=forms.RadioSelect,
    )
    accepted = forms.BooleanField(label="I have saved my recovery codes")
    token = forms.CharField(widget=forms.HiddenInput, required=False)


def valid_data() -> dict[str, str]:
    return {
        "email": "ada@example.com",
        "display_name": "Ada",
        "contact_preference": "email",
        "accepted": "on",
    }


def render_field(form: forms.Form, name: str) -> str:
    return render_to_string("partials/field.html", {"field": form[name]})


class FieldPartialTests(SimpleTestCase):
    def test_label_is_associated_with_its_control(self):
        html = render_field(SampleForm(), "email")

        self.assertIn('<label class="field__label" for="id_email">', html)
        self.assertIn('id="id_email"', html)

    def test_required_field_states_that_in_words_not_only_an_asterisk(self):
        html = render_field(SampleForm(), "email")

        self.assertIn('<span class="field__required" aria-hidden="true">*</span>', html)
        self.assertIn('<span class="visually-hidden"> (required)</span>', html)
        # The control itself says so too, which is what a screen reader reads.
        self.assertRegex(html, r"<input[^>]*\brequired\b[^>]*>")

    def test_optional_field_has_no_required_marker(self):
        html = render_field(SampleForm(), "nickname")

        self.assertNotIn("field__required", html)
        self.assertNotIn("(required)", html)

    def test_help_text_carries_the_id_the_control_describes_itself_with(self):
        html = render_field(SampleForm(), "email")

        self.assertIn('id="id_email_helptext"', html)
        self.assertIn('aria-describedby="id_email_helptext"', html)

    def test_errored_control_is_invalid_and_points_at_its_own_error_list(self):
        form = SampleForm({})
        form.is_valid()

        html = render_field(form, "email")

        self.assertIn('aria-invalid="true"', html)
        self.assertIn('id="id_email_error"', html)
        # Both descriptions, in the order Django builds them.
        self.assertIn('aria-describedby="id_email_helptext id_email_error"', html)

    def test_error_is_announced_as_text_not_only_as_colour(self):
        form = SampleForm({})
        form.is_valid()

        html = render_field(form, "display_name")

        self.assertIn('<span class="visually-hidden">Error: </span>', html)
        self.assertIn("This field is required.", html)

    def test_errored_field_wrapper_is_marked_for_styling(self):
        form = SampleForm({})
        form.is_valid()

        self.assertIn("field--invalid", render_field(form, "email"))
        self.assertNotIn("field--invalid", render_field(SampleForm(), "email"))

    def test_error_precedes_the_control_it_belongs_to(self):
        form = SampleForm({})
        form.is_valid()

        html = render_field(form, "display_name")

        self.assertLess(html.index("This field is required."), html.index('id="id_display_name"'))

    def test_checkbox_label_follows_its_control(self):
        html = render_field(SampleForm(), "accepted")

        label = "I have saved my recovery codes"
        self.assertLess(html.index('id="id_accepted"'), html.index(label))
        self.assertIn('for="id_accepted"', html)

    def test_group_of_controls_uses_a_fieldset_and_legend(self):
        html = render_field(SampleForm(), "contact_preference")

        self.assertIn('<legend class="field__legend">', html)
        self.assertIn('id="id_contact_preference_fieldset"', html)
        # Focusable so the error summary can send focus to the group.
        self.assertIn('tabindex="-1"', html)
        self.assertNotIn('<label class="field__label"', html)

    def test_hidden_field_renders_bare(self):
        html = render_field(SampleForm(), "token")

        self.assertIn('type="hidden"', html)
        self.assertNotIn('class="field', html)


INJECTION = '<img src=x onerror="alert(1)">'


class HelpTextForm(forms.Form):
    """Help text in each of the three shapes `partials/field.html` renders.

    The values stand in for help text built from something a user controls --
    an email address, a display name -- which is what most of these screens
    want to show.
    """

    plain = forms.CharField(label="Plain", help_text=INJECTION)
    checkbox = forms.BooleanField(label="Checkbox", help_text=INJECTION)
    group = forms.ChoiceField(
        label="Group",
        choices=[("a", "A"), ("b", "B")],
        widget=forms.RadioSelect,
        help_text=INJECTION,
    )
    marked_up = forms.CharField(
        label="Marked up",
        help_text=format_html('Read the <a href="{}">guide</a>.', "/help"),
    )


class HelpTextEscapingTests(SimpleTestCase):
    """Help text is escaped, so no field can become an HTML injection sink.

    This is a deliberate deviation from Django's own `django/forms/field.html`,
    which applies `|safe`. Every screen in increment 1 inherits this partial,
    and there is no CSP yet, so the default has to be the safe one.
    """

    def test_help_text_is_escaped_in_every_field_shape(self):
        for name in ("plain", "checkbox", "group"):
            with self.subTest(field=name):
                html = render_field(HelpTextForm(), name)

                self.assertNotIn(INJECTION, html)
                self.assertNotIn("<img", html)
                self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", html)

    def test_help_text_that_is_explicitly_marked_safe_still_renders_as_markup(self):
        html = render_field(HelpTextForm(), "marked_up")

        self.assertIn('Read the <a href="/help">guide</a>.', html)

    def test_the_partial_pipes_help_text_through_no_filter(self):
        """A regression guard, for a shape added later that these tests miss."""
        source = (settings.BASE_DIR / "templates" / "partials" / "field.html").read_text()

        self.assertNotRegex(source, r"field\.help_text\s*\|")


class ErrorSummaryTests(SimpleTestCase):
    def render_summary(self, form: SampleForm, **context: str) -> str:
        return render_to_string("partials/form_errors.html", {"form": form, **context})

    def test_absent_when_the_form_has_no_errors(self):
        form = SampleForm(valid_data())
        self.assertTrue(form.is_valid())

        self.assertEqual(self.render_summary(form).strip(), "")

    def test_is_an_alert_region(self):
        form = SampleForm({})
        form.is_valid()

        html = self.render_summary(form)

        self.assertIn('role="alert"', html)
        self.assertIn("There is a problem", html)
        # Focusable, so error-summary.js can move focus here on load.
        self.assertIn('tabindex="-1"', html)
        self.assertIn("data-error-summary", html)

    def test_lists_form_level_errors_that_belong_to_no_field(self):
        form = SampleForm(valid_data())
        form.add_error(None, "Incorrect email or password.")

        html = self.render_summary(form)

        self.assertIn("Incorrect email or password.", html)

    def test_each_field_error_names_its_field_and_links_to_the_control(self):
        form = SampleForm({})
        form.is_valid()

        html = self.render_summary(form)

        self.assertIn('<a href="#id_email">Email: This field is required.</a>', html)
        self.assertIn("#id_display_name", html)

    def test_group_error_links_to_the_fieldset_because_it_has_no_single_control(self):
        form = SampleForm({})
        form.is_valid()

        self.assertIn('href="#id_contact_preference_fieldset"', self.render_summary(form))

    def test_ids_are_namespaced_so_two_forms_can_share_a_page(self):
        form = SampleForm({})
        form.is_valid()

        html = self.render_summary(form, form_id="display-name")

        self.assertIn('id="display-name-errors"', html)
        self.assertIn('aria-labelledby="display-name-errors-title"', html)


class FormPartialTests(SimpleTestCase):
    def render_form(self, **context) -> str:
        base = {"form": SampleForm(), "csrf_token": "a-csrf-token"}
        return render_to_string("partials/form.html", {**base, **context})

    def test_posts_by_default(self):
        self.assertIn('method="post"', self.render_form())

    def test_carries_a_csrf_token(self):
        self.assertIn('name="csrfmiddlewaretoken" value="a-csrf-token"', self.render_form())

    def test_a_get_form_carries_no_csrf_token(self):
        self.assertNotIn("csrfmiddlewaretoken", self.render_form(method="get"))

    def test_skips_native_validation_so_the_server_reports_every_error_at_once(self):
        self.assertIn("novalidate", self.render_form())

    def test_renders_every_visible_field_and_a_submit_button(self):
        html = self.render_form(submit_label="Create account")

        self.assertIn('for="id_email"', html)
        self.assertIn('for="id_display_name"', html)
        self.assertIn('<button type="submit" class="button">Create account</button>', html)

    def test_submit_label_falls_back_to_save(self):
        self.assertIn(">Save</button>", self.render_form())

    def test_action_is_omitted_unless_given(self):
        self.assertNotIn("action=", self.render_form())
        self.assertIn('action="/signup"', self.render_form(action="/signup"))
