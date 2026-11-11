"""The reference page for the shared template layer.

Every increment 1 screen renders its forms through ``templates/partials/``.
This page renders those partials in each state they can be in -- empty, with
field errors, with a form-level error, and after a valid submission -- so the
markup and the accessibility baseline can be checked in a browser on a preview
environment without first building a real feature, and so a regression in the
shared layer shows up in one place instead of in four screens at once.

It is not product surface. ``UI_REFERENCE_ENABLED`` is False everywhere except
developer machines and preview environments, and the view 404s when it is off.
"""

from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render


class ReferenceForm(forms.Form):
    """One field of every shape the field partial has to handle.

    A text input, an input with help text, a password input, a widget that
    needs a fieldset and legend rather than a single label, and a lone
    checkbox. The validation rules mirror the increment 1 brief closely enough
    to produce realistic errors; nothing here is used by the product.
    """

    email = forms.EmailField(
        label="Email",
        max_length=254,
        help_text="The address you sign in with.",
    )
    display_name = forms.CharField(label="Display name", max_length=80)
    password = forms.CharField(
        label="Password",
        min_length=12,
        max_length=128,
        widget=forms.PasswordInput,
        help_text="At least 12 characters. Spaces count.",
    )
    contact_preference = forms.ChoiceField(
        label="How should we contact you?",
        choices=[("email", "By email"), ("none", "Do not contact me")],
        widget=forms.RadioSelect,
    )
    accepted = forms.BooleanField(label="I have saved my recovery codes")


# Deliberately invalid: an unparseable address, a missing display name, a
# password under the minimum, and nothing chosen in the radio group. The
# checkbox is absent, which is how an unticked checkbox arrives.
INVALID_SAMPLE = {
    "email": "not-an-email",
    "display_name": "",
    "password": "short",
    "contact_preference": "",
}


def _form_with_errors() -> ReferenceForm:
    """A bound form carrying both field errors and a form-level error."""
    form = ReferenceForm(INVALID_SAMPLE)
    form.is_valid()
    # A form-level error belongs to no field. Sign-in produces exactly this
    # shape -- "Incorrect email or password" names neither input -- so the
    # partials have to render it somewhere, and this is where that is checked.
    form.add_error(None, "Incorrect email or password.")
    return form


def reference_page(request: HttpRequest) -> HttpResponse:
    if not settings.UI_REFERENCE_ENABLED:
        raise Http404("The template reference page is disabled in this environment.")

    if request.method == "POST":
        form = ReferenceForm(request.POST)
        if form.is_valid():
            messages.success(request, "That submission was valid. Nothing was saved.")
            return redirect("core:ui_reference")
    elif request.GET.get("state") == "errors":
        form = _form_with_errors()
    else:
        form = ReferenceForm()

    return render(request, "core/ui_reference.html", {"form": form})
