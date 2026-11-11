# Templates, forms and the accessibility baseline

The shared template layer every increment 1 screen is built on. Server-rendered
Django templates; no SPA and no frontend build step in increment 1 (ADR-0001).

## What is here

| File | Purpose |
| --- | --- |
| `templates/base.html` | Document head, skip link, header, `main` landmark, flash messages |
| `templates/partials/messages.html` | `django.contrib.messages`, as a polite live region |
| `templates/partials/form.html` | A complete `<form>`: method, CSRF, summary, fields, submit |
| `templates/partials/form_body.html` | The inside of a form, for pages that need their own `<form>` |
| `templates/partials/form_errors.html` | The error summary: form-level errors, then one link per field error |
| `templates/partials/field.html` | One field: label, help text, errors, control |
| `templates/partials/field_errors.html` | The error list for one field |
| `templates/partials/required_marker.html` | The visible and the spoken "required" |
| `static/css/base.css` | The whole stylesheet |
| `static/js/error-summary.js` | Moves focus to the error summary after a failed submission |

## Using it

The common case is one form and one submit button:

```html
{% extends "base.html" %}

{% block content %}
  <h1>Create your account</h1>
  {% include "partials/form.html" with form=form submit_label="Create account" %}
{% endblock %}
```

`partials/form.html` accepts `form` (required) and optionally `action`,
`method` (default `post`), `form_id`, `form_class` and `submit_label`.

**Do not add `only` to the include.** `{% csrf_token %}` reads the token from
the surrounding context, and `only` removes it.

When a page needs more than one button, or content between fields, write the
`<form>` yourself and include the body:

```html
<form method="post" novalidate>
  {% csrf_token %}
  {% include "partials/form_body.html" with form=form form_id="display-name" %}
  <div class="form-actions">
    <button type="submit" class="button">Save</button>
    <button type="submit" name="action" value="cancel" class="button button--secondary">Cancel</button>
  </div>
</form>
```

Pass `form_id` whenever a page carries more than one form -- the account page
does. It namespaces the error summary's ids so two summaries cannot collide.

## The baseline

These hold for every screen built on these partials. They are asserted in
`alfulk/core/tests/test_template_partials.py` and
`alfulk/core/tests/test_base_template.py`; a change that breaks one fails CI.

- **Every control has a programmatically associated label.** A `<label for>`,
  or a `<legend>` inside a `<fieldset>` where one label cannot describe a group
  of radios or checkboxes.
- **Errors are associated with their field.** Django 5's `BoundField` adds
  `aria-invalid="true"` and an `aria-describedby` naming `<auto_id>_helptext`
  and `<auto_id>_error`; the partials emit elements with exactly those ids. If
  you render a control by hand, you take on that wiring yourself.
- **Help text is escaped.** `partials/field.html` renders `field.help_text`
  without `|safe`, deliberately unlike Django's own field template. Help text
  on these screens carries user-controlled values -- an email address, a
  display name -- so escaping has to be what you get by not thinking about it.
  A field that needs markup opts in where it is defined, with `format_html()`
  or `mark_safe()`:

  ```python
  help_text = format_html('See the <a href="{}">recovery guide</a>.', url)
  ```

  Never by reaching for `|safe` in the template: that re-opens it for every
  field, including the ones built from user input.
- **Error state is never carried by colour alone.** Each message is prefixed
  with a visually hidden "Error:", the control is `aria-invalid`, and the red
  border is the third signal rather than the only one.
- **The error summary is announced.** `role="alert"`, plus
  `static/js/error-summary.js` moving focus to it on load, because a live
  region that was already in the document when it loaded is not reliably
  announced. With JavaScript off the summary is still rendered and still links
  to each field.
- **Focus is visible and never removed.** `outline: none` without a
  replacement indicator is a defect, not a style choice.
- **Every page is operable by keyboard alone.** The skip link is the first
  focusable element and targets the `main` landmark, which carries
  `tabindex="-1"` so focus actually moves.

## Why forms carry `novalidate`

Native browser validation stops at the first invalid control. The brief
requires that a rejected submission shows every error at once (AC-SU-5), and
browser validation bubbles are neither styleable nor consistently announced.
The controls keep `required`, `type="email"` and `maxlength` -- those describe
the field to assistive technology -- but the server is the only thing that
decides whether a submission is valid.

## Seeing it

`/_ui/forms` renders the partials in every state: empty, with field errors, and
with a form-level error. It is served only where `UI_REFERENCE_ENABLED` is set,
which is developer machines and preview environments. The page carries its own
keyboard checklist for a reviewer to work through.

## Checking a new screen

1. Tab from the top. The skip link appears first and is visible.
2. Every control is reachable, in reading order, with a visible focus ring.
3. Submit it empty. Focus lands on the summary; each entry names its field and
   moves focus to that control.
4. Zoom to 200%. Nothing is clipped or overlapped.
5. Switch the operating system to dark mode. Contrast still holds.
