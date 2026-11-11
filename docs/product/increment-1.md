# Increment 1 brief: Identity & Sign-in (M1, part 1)

Status: draft for confirmation (owner: Product Manager). Last updated 2026-11-11.

Increment 1 delivers a single user's account life cycle with no organization,
no admin, and no outbound email. Everything below must be checkable on staging
with synthetic data by someone who did not build it.

Acceptance criteria are numbered (`AC-xx-n`) so the CTO can map them to
engineering tasks and QA can map them to test cases. A criterion is met only
when QA can reproduce it on staging.

## Scope

In scope:

1. Sign-up with email, display name, and a password of at least 12 characters
2. Sign-in and sign-out with secure session cookies and an idle timeout
3. An account page
4. Enabling TOTP two-factor with a QR code and one-time recovery codes
5. Signing in with a TOTP code or a recovery code
6. Lockout after repeated failed sign-ins
7. An audit log of sign-in events, visible to the user

Not in increment 1 (see `plan.md` for the full list): email verification,
password reset, change email, change password, organizations, admin,
"Sign in with Alfulk", passkeys, session list with remote sign-out, account
deletion, any email sending.

## Defaults used in this brief

These values are product defaults. Engineering may change the mechanism, not
the user-visible behavior, and each must be configurable per environment so
QA can test them quickly on staging (see "Staging and synthetic data").

| Setting | Default | Staging note |
| --- | --- | --- |
| Password minimum length | 12 characters | fixed |
| Password maximum length | 128 characters | fixed |
| Display name length | 1 to 80 characters after trimming | fixed |
| Session idle timeout | 30 minutes, sliding | configurable down to 1 minute |
| Session absolute lifetime | 12 hours | configurable down to 5 minutes |
| Two-factor second step must finish within | 5 minutes of the password step | configurable |
| Failed sign-in attempts before lockout | 10 within 15 minutes, per account | configurable |
| Lockout duration | 15 minutes | configurable |
| TOTP | RFC 6238, 6 digits, 30-second step, SHA-1, accept one step of clock drift either side | fixed |
| Recovery codes | 10 codes per set, 10 characters each, shown as `xxxxx-xxxxx`, each usable once | fixed |
| Audit log shown on the account page | last 20 sign-in events | fixed |

## 1. Sign-up

### Expected behavior

- A visitor opens `/signup`, enters email, display name, password, and
  password confirmation, and submits.
- On success the account exists, the visitor is signed in, and lands on the
  account page. No email is sent and no verification step exists in this
  increment.
- The password is stored only as a hash (Argon2id per the stack ADR). The
  plaintext never appears in logs, the database, or the audit log.
- Email is the sign-in identifier. It is stored as entered but matched
  case-insensitively after trimming whitespace. `Ada@Example.com` and
  `ada@example.com` are the same account.

### Validation rules

- Email: required, trimmed, must be a syntactically valid address, maximum
  254 characters, unique case-insensitively.
- Display name: required, trimmed, 1 to 80 characters, no control characters.
  Any printable Unicode is allowed.
- Password: required, 12 to 128 characters, any characters including spaces
  and Unicode. No composition rules (no "one uppercase, one digit"). Rejected
  if it appears on the common-password list or is too similar to the email or
  display name. Confirmation must match exactly.
- All errors are shown next to the field, at once, with the entered email and
  display name preserved and the password fields cleared.

### Edge cases

- Duplicate email (any letter case, any surrounding whitespace): the form shows
  "An account with this email already exists" with a link to sign in. This
  reveals that the address is registered. We accept that for increment 1
  because there is no email delivery to do the usual "we sent you a message
  either way" pattern. Revisit when email verification ships.
- Password of exactly 11 characters: rejected. Exactly 12: accepted.
- Password of 129 characters: rejected with a message stating the maximum.
- Password equal to the email or display name, or a trivial variant: rejected.
- Leading or trailing spaces in a password are kept, not trimmed.
- Two sign-ups with the same email submitted at the same moment: exactly one
  succeeds; the database enforces uniqueness, not only the form.
- A signed-in user who opens `/signup` is redirected to the account page.
- The form is protected against cross-site request forgery.

### Acceptance criteria

- AC-SU-1: Submitting valid email, display name, and a 12-character password
  creates the account, signs the user in, and shows the account page with the
  display name and email.
- AC-SU-2: An 11-character password is rejected with a message naming the
  12-character minimum; the account is not created.
- AC-SU-3: A password on the common-password list (for example
  `password12345`) is rejected; the account is not created.
- AC-SU-4: Signing up with an email that differs from an existing account only
  by letter case or surrounding whitespace is rejected with the duplicate
  message and a sign-in link.
- AC-SU-5: An invalid email, an empty display name, an 81-character display
  name, and a mismatched confirmation each show a field-level error, all in the
  same submission, with email and display name preserved and passwords cleared.
- AC-SU-6: After sign-up the audit log shows one `account_created` event and
  one `signin_succeeded` event for the new account.
- AC-SU-7: The stored password is an Argon2id hash. No plaintext password
  appears in application logs or the database for any synthetic account.

## 2. Sign-in and sign-out

### Expected behavior

- `/signin` asks for email and password. On success the user lands on the page
  they originally asked for if it is on this site, otherwise the account page.
- If the account has two-factor enabled, a correct password leads to the
  second step (section 5) and the user is not signed in until it completes.
- Failure shows the single message "Incorrect email or password" whether the
  email is unknown, the password is wrong, or the account is locked out (see
  section 6 for the lockout message rule).
- Sign-out is a POST from a button available on every signed-in page. It
  destroys the server-side session and clears the cookie, then shows the
  sign-in page with "You have been signed out."

### Session rules

- The session cookie is `HttpOnly`, `Secure`, `SameSite=Lax`, scoped to the
  host, and contains only an opaque session identifier. Nothing about the user
  is readable from the cookie.
- The session identifier is rotated on successful sign-in, after the second
  factor completes, and on sign-out.
- Idle timeout: a session that has had no request for the idle timeout
  (default 30 minutes) is invalid. Any request within the window extends it.
- Absolute lifetime: no session lives longer than 12 hours after sign-in,
  regardless of activity.
- When either limit is hit, the next request to a signed-in page redirects to
  `/signin?next=<original path>` with the message "Your session expired.
  Please sign in again." and an `session_expired` audit event is recorded.
- Sign-out invalidates the session server-side. Presenting the old cookie
  afterwards is treated as signed out.

### Edge cases

- Email entered with different letter case or surrounding whitespace matches
  the account.
- A `next` parameter pointing to another host or a protocol-relative URL is
  ignored and the user lands on the account page.
- A signed-in user who opens `/signin` is redirected to the account page.
- Two browsers signed in to the same account have independent sessions.
  Signing out of one does not sign out the other (remote sign-out is not in
  this increment).
- A sign-in attempt for a non-existent email takes about as long as one for a
  real email with a wrong password, so timing does not reveal which emails
  exist. Engineering decides the mechanism (for example always running the
  hash).
- Sign-out by GET is not allowed. The sign-out endpoint rejects GET.

### Acceptance criteria

- AC-SI-1: Correct email and password for an account without two-factor signs
  the user in and shows the account page.
- AC-SI-2: Wrong password, unknown email, and an email with different letter
  case plus a wrong password all show exactly "Incorrect email or password".
- AC-SI-3: The session cookie has the `HttpOnly`, `Secure`, and
  `SameSite=Lax` attributes and its value changes between before and after a
  successful sign-in.
- AC-SI-4: With the staging idle timeout set to 1 minute, a signed-in user who
  waits 90 seconds and then opens the account page is redirected to sign-in
  with the session-expired message. A user who reloads every 30 seconds for 3
  minutes stays signed in.
- AC-SI-5: With the staging absolute lifetime set to 5 minutes, a user who
  reloads every 30 seconds is still redirected to sign-in after 5 minutes.
- AC-SI-6: After sign-out, replaying the previous session cookie to the
  account page redirects to sign-in.
- AC-SI-7: Visiting `/account` while signed out redirects to
  `/signin?next=/account`, and signing in then lands on `/account`. A `next`
  of `https://evil.example/` lands on `/account` instead.
- AC-SI-8: Sign-in success, sign-in failure, sign-out, and session expiry each
  create the matching audit event (section 7).

## 3. Account page

### Expected behavior

`/account` is the signed-in home. It shows:

- Email (read-only in this increment) and display name, with an inline form to
  change the display name (same rules as sign-up).
- Two-factor status: "Off" with an "Turn on two-factor" button, or "On since
  <date>" with "Show new recovery codes" and "Turn off two-factor" actions and
  the count of unused recovery codes.
- Recent sign-in activity: the last 20 audit events for this account (section
  7), newest first.
- Account created date and a sign-out button.

### Edge cases

- Changing the display name to the same value is a no-op with no error.
- An empty or whitespace-only display name is rejected and the previous value
  stays.
- The page must be served only to the signed-in user; it never shows another
  user's data even if a user id is placed in the URL.
- All forms on the page are POST with CSRF protection.

### Acceptance criteria

- AC-AP-1: A signed-in user sees their email, display name, two-factor status,
  created date, and recent sign-in activity on `/account`.
- AC-AP-2: Changing the display name to a valid value updates it immediately on
  the page and on later visits; an invalid value shows a field error and keeps
  the previous name.
- AC-AP-3: `/account` cannot be viewed signed out (redirects to sign-in).

## 4. Enabling TOTP two-factor

### Expected behavior

- From the account page, "Turn on two-factor" asks for the current password
  first (re-authentication), then shows the setup page.
- The setup page shows a QR code encoding an `otpauth://totp/` URI with issuer
  `Alfulk`, the account email as the label, and a fresh secret. The same secret
  is shown as text for manual entry, grouped in blocks of four.
- The user enters one code from their authenticator app. A correct code turns
  two-factor on and shows the recovery codes page once.
- The recovery codes page shows 10 codes, a "Download as text file" action, a
  "Copy" action, and a checkbox "I have saved these codes" that must be ticked
  before "Done" returns to the account page. The codes are never shown again.
  "Show new recovery codes" on the account page generates a new set and
  invalidates all previous codes.
- Recovery codes are stored hashed (HMAC per the stack ADR). Each is usable
  exactly once.
- "Turn off two-factor" asks for the current password and a current TOTP code,
  then disables two-factor and deletes the secret and all recovery codes.

### Edge cases

- Leaving the setup page before entering a valid code leaves two-factor off.
  Reopening setup generates a new secret; the old one never becomes active.
- A wrong code on setup shows "That code is not correct. Check the time on your
  device and try again." and keeps the same secret so the user does not need to
  rescan.
- A code from the previous or next 30-second step is accepted (clock drift).
  A code older than that is rejected.
- The same TOTP code cannot be used twice (replay). The second use within the
  same step is rejected, both on setup and on sign-in.
- Five wrong codes in a row on the setup page end the setup; the user must
  start again (new secret).
- Regenerating recovery codes requires the password again. Old codes stop
  working the moment the new set is created, even if the user never saves the
  new set.
- A user who turns two-factor off and on again gets a new secret and a new set
  of recovery codes.

### Acceptance criteria

- AC-2F-1: After entering the correct password, the setup page shows a QR code
  and the text secret; scanning the QR with a standard authenticator app
  (Google Authenticator, Aegis, 1Password, or an `oathtool` command using the
  text secret) produces codes the setup page accepts.
- AC-2F-2: Entering a wrong code keeps two-factor off and keeps the same secret
  on the page. The fifth consecutive wrong code ends the setup with a message
  and a new secret on the next attempt.
- AC-2F-3: A correct code turns two-factor on and shows exactly 10 recovery
  codes in `xxxxx-xxxxx` form, with download and copy actions, and "Done" is
  disabled until the saved checkbox is ticked.
- AC-2F-4: After "Done", the account page shows two-factor "On" with 10 unused
  recovery codes, and the codes are not retrievable anywhere in the UI.
- AC-2F-5: "Show new recovery codes" (with the password) shows a different set
  of 10, and a code from the old set no longer signs in.
- AC-2F-6: "Turn off two-factor" with the password and a current code sets the
  status to "Off"; a later sign-in needs only the password.
- AC-2F-7: Recovery codes and the TOTP secret are not stored in plaintext in
  the database: the recovery codes are stored as HMAC hashes and the secret is
  encrypted at rest (mechanism per ADR).
- AC-2F-8: Enabling, disabling, and regenerating recovery codes each create the
  matching audit event.

## 5. Signing in with two-factor or a recovery code

### Expected behavior

- After a correct password on an account with two-factor on, the user sees a
  second step asking for a 6-digit code, with a link "Use a recovery code
  instead" that switches the field to accept a recovery code.
- A correct TOTP code or an unused recovery code completes sign-in. A used
  recovery code is consumed immediately and the account page shows the reduced
  unused count.
- The second step must complete within 5 minutes of the password step. After
  that the user starts over at email and password.
- Between the password step and the second step, the user is not signed in:
  any signed-in page redirects to sign-in, and the pending state is bound to
  the browser that passed the password step.

### Edge cases

- Wrong or expired TOTP code, or an unknown or already-used recovery code:
  "That code is not correct." The counter in section 6 is incremented, so
  guessing codes leads to the same lockout as guessing passwords.
- Recovery code entry ignores letter case, spaces, and the hyphen.
- When the last unused recovery code is used, sign-in completes and the account
  page shows a warning "You have no recovery codes left. Generate new ones."
- If two-factor is turned off between the password step and the second step
  (for example from another session), the second step fails and the user
  signs in again.
- A TOTP code that was already used to complete a previous sign-in within the
  same 30-second step is rejected.
- Reloading the second-step page does not resubmit anything and keeps the
  5-minute window.

### Acceptance criteria

- AC-2S-1: With two-factor on, correct email and password show the second
  step, and `/account` is still unreachable until it is completed.
- AC-2S-2: A current TOTP code completes sign-in and shows the account page.
- AC-2S-3: A previously used TOTP code within the same step is rejected.
- AC-2S-4: An unused recovery code (entered in any letter case, with or
  without the hyphen) completes sign-in and the unused count decreases by one.
- AC-2S-5: The same recovery code entered again on a later sign-in is rejected.
- AC-2S-6: With the staging second-step window set to 1 minute, waiting 90
  seconds before submitting a correct code returns the user to the email and
  password step with an explanatory message.
- AC-2S-7: Using the last recovery code completes sign-in and shows the
  "no recovery codes left" warning on the account page.
- AC-2S-8: Second-step success, second-step failure, and recovery-code use
  each create the matching audit event.

## 6. Lockout after repeated failed sign-ins

### Expected behavior

- Failed attempts are counted per submitted email (normalized), whether or not
  an account with that email exists, and whether the failure was a wrong
  password, a wrong TOTP code, or a wrong recovery code.
- After 10 failures within 15 minutes, further sign-in attempts for that email
  are rejected for 15 minutes even if the password is correct.
- While locked, the sign-in form shows "Too many failed attempts. Try again in
  about N minutes." Because the counter exists for unknown emails too, this
  message does not reveal whether the account exists.
- A successful sign-in resets the counter for that email. The lock expires on
  its own; there is no admin unlock in this increment.
- The lockout state must survive an application restart (stored in the
  database or shared cache, not in process memory).

### Edge cases

- The 10th failure triggers the lock; the 11th attempt is rejected even with
  the correct password.
- Failures are counted the same for `Ada@Example.com` and `ada@example.com`.
- Two-factor failures in the second step count towards the same counter as
  password failures.
- Lockout is per email, so one locked email does not affect sign-in to other
  accounts from the same browser.
- Lockout does not sign out an already signed-in session of that account.
- Failures older than 15 minutes no longer count. Nine failures, a 16-minute
  pause, and one more failure do not lock.

### Acceptance criteria

- AC-LO-1: With staging configured to 3 failures and a 2-minute lock, three
  wrong passwords lock the email: the fourth attempt with the correct password
  is rejected with the "Too many failed attempts" message.
- AC-LO-2: The same sequence for an email that has no account produces the
  same messages and the same lock.
- AC-LO-3: After the lock duration passes, the correct password signs in.
- AC-LO-4: Two wrong passwords followed by one wrong TOTP code (on an account
  with two-factor) lock the email.
- AC-LO-5: A successful sign-in after two failures resets the counter: two
  more failures do not lock.
- AC-LO-6: Restarting the application while an email is locked does not clear
  the lock.
- AC-LO-7: The lock and each counted failure appear in the audit log as
  `signin_failed` events and one `account_locked` event.

## 7. Audit log of sign-in events

### Expected behavior

Every event below is recorded with: event type, timestamp (UTC), the account it
concerns (or the normalized email for failures without an account), the client
IP address (respecting the deployment's proxy configuration), and the user
agent string. Events are append-only: nothing in the application updates or
deletes them.

| Event type | When |
| --- | --- |
| `account_created` | sign-up succeeded |
| `signin_succeeded` | session established (after the second factor if enabled) |
| `signin_failed` | wrong password, unknown email, or failed second step; includes a `reason` of `bad_password`, `unknown_email`, `bad_totp`, `bad_recovery_code`, or `locked` |
| `second_factor_required` | password accepted, second step shown |
| `recovery_code_used` | sign-in completed with a recovery code; includes the number of codes left |
| `account_locked` | failure threshold reached |
| `signout` | user signed out |
| `session_expired` | idle or absolute limit hit on a request |
| `two_factor_enabled` | setup completed |
| `two_factor_disabled` | turned off |
| `recovery_codes_regenerated` | new set generated |
| `display_name_changed` | account page edit |

The user sees their own events (not `unknown_email` events, which have no
account) on the account page: the last 20, newest first, with a readable
label, time, IP, and a shortened browser description.

### Edge cases

- Passwords, TOTP codes, recovery codes, and secrets never appear in an event.
- Events for an email that has no account are stored under the email so the
  lockout rule can use them, and are not shown to anyone in this increment.
- If recording the event fails, the sign-in itself still fails closed for
  security-relevant events: a sign-in whose success event cannot be written is
  not completed.
- Times are stored in UTC and shown in UTC with a `UTC` suffix; time zones per
  user are a later increment.

### Acceptance criteria

- AC-AL-1: Each event type in the table can be produced on staging by the
  action in the "When" column and appears in the database with type, UTC
  timestamp, account or email, IP, and user agent.
- AC-AL-2: The account page shows the signed-in user's last 20 events, newest
  first, and does not show events from any other account.
- AC-AL-3: After 25 sign-in events, the account page shows 20; all 25 exist in
  the database.
- AC-AL-4: No event row contains a password, TOTP code, recovery code, or TOTP
  secret for any synthetic account (checked by searching event rows for the
  known synthetic values).
- AC-AL-5: There is no application path that edits or deletes audit events.

## Staging and synthetic data

Everything in this brief must be checkable on staging by QA without production
data and without building the software. Engineering provides:

- **A seed command** that creates these synthetic accounts, idempotently, with
  known passwords recorded in the staging runbook (never in this document):
  - `alice@staging.alfulk.test`: two-factor off.
  - `bob@staging.alfulk.test`: two-factor on, with the TOTP secret and the 10
    recovery codes printed by the seed command so QA can generate codes with
    `oathtool` and test recovery codes.
  - `carol@staging.alfulk.test`: two-factor on, exactly one unused recovery
    code left.
  - Alice has at least 25 sign-in events, so the account page cap is testable
    without clicking 25 times.
- **Environment-configurable timings and thresholds** (section "Defaults"),
  set on staging to the fast values used in the acceptance criteria above:
  1-minute idle timeout, 5-minute absolute lifetime, 1-minute second-step
  window, 3 failures and 2-minute lockout. Production uses the defaults.
- **A way to read audit events** on staging for AC-AL-1, AC-AL-3, and AC-AL-4:
  either a read-only management command that prints events for an email, or
  read-only database access for QA.
- **A way to inspect cookies** is standard browser tooling; no engineering work.
- **A reset command** that deletes all synthetic accounts and their events so a
  test run starts clean.

QA is expected to write one test case per acceptance criterion and to run them
on staging before each increment 1 release. Automated tests in the repository
should cover the same criteria where practical, but the staging pass is the
release gate.

## Questions for the CTO

Technical questions that do not change the user-visible behavior above. The
CTO decides; the brief is updated only if a decision changes behavior.

1. Where do the lockout counters live (database table or cache) so they survive
   restarts and work with multiple application processes?
2. How is the TOTP secret encrypted at rest, and where does the key come from
   per environment?
3. How do we get a reliable client IP behind the chosen hosting provider's
   proxy for the audit log?
4. Is the "pending second factor" state kept in the session store or in a
   separate signed token? Either is fine if it meets section 5.
5. Can staging run with the fast timing values above without affecting preview
   environments?

## Open product decisions for the user

1. Is revealing "an account with this email already exists" on sign-up
   acceptable for increment 1, given there is no email delivery yet? (This
   brief says yes.)
2. Idle timeout of 30 minutes and absolute lifetime of 12 hours: confirm or
   choose other defaults.
3. Lockout of 10 failures in 15 minutes with a 15-minute lock: confirm or
   choose other defaults.
