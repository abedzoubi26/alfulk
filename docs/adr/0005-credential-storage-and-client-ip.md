# ADR-0005: Credential storage at rest, and resolving the client IP

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** CTO
- **Supersedes:** [ADR-0001](0001-technology-stack.md) in part — its TOTP
  encryption choice (Fernet / `MultiFernet`). Everything else in ADR-0001
  stands.

## Context

Increment 1 introduces three pieces of state that the rest of the platform will
inherit, and all three are easy to get wrong in ways that are invisible until
they matter:

1. **The TOTP secret.** It is the only credential in M1 that we must be able to
   read back. Passwords and recovery codes are hashed — verification compares
   hashes and never needs the original. A TOTP secret cannot work that way:
   generating the expected code requires the secret itself. So it is stored
   encrypted, and a storage format has to be chosen now, because changing it
   later is a data migration over the most sensitive column we have.

2. **Lockout counters.** AC-LO-1…7 require counting failed sign-ins per email,
   surviving a restart, across processes.

3. **The client IP in audit events.** AC-AL-1…5 require recording where a
   sign-in came from. The application sits behind a reverse proxy, so
   `REMOTE_ADDR` is the proxy, and the obvious replacement —
   `X-Forwarded-For` — is partly attacker-controlled.

ADR-0001 commits us to no Redis in increment 1, which constrains (2).

## Decision

### 1. TOTP secrets: AES-256-GCM, encrypted application-side

`cryptography`'s `AESGCM`, fresh random 96-bit nonce per encryption. Stored as:

```
v1.<kid>.<base64url(nonce || ciphertext || tag)>
```

**AAD is `b"totp-secret:" + str(user_id)`.** This binds the ciphertext to its
row. A ciphertext lifted from another user's row fails to decrypt rather than
silently authenticating someone with a stranger's secret.

Key material lives in `TOTP_SECRET_ENCRYPTION_KEYS`: an ordered,
comma-separated list of `kid:base64key`, 32 random bytes each. The first entry
encrypts; any entry may decrypt.

The list is not over-engineering. With a single key, rotation is an outage —
every user's second factor breaks at once with no migration path. With a key
list and the `kid` in the column, rotation is a `rotate_totp_keys` command that
re-encrypts rows under the new id, after which the old key leaves the
environment.

Keys are generated independently per environment and never shared (ADR-0003).

**The unconfirmed secret never touches the user row.** During enrolment it is
held as the same encrypted envelope inside the pending session state, with AAD
`totp-enrolment:<user_id>`. This is load-bearing: Django session data is
*signed, not encrypted*, and ADR-0001 stores sessions in the database — so a
raw pending secret in the session would be a plaintext TOTP secret sitting in
`django_session`. On confirmation it is re-encrypted under the `totp-secret:`
AAD. The differing AAD means a pending envelope cannot be promoted by copying
bytes.

#### Rejected

- **pgcrypto.** The key appears in SQL statement text, and therefore in
  `log_statement` output, `pg_stat_activity`, and any query log. Encrypting
  application-side keeps the key out of the database process entirely.
- **Disk or volume encryption.** Protects a stolen disk and nothing else. Not a
  `pg_dump`, not a backup in object storage — which is exactly where ADR-0002
  puts them — not a replica, not a SQL-injection read. Those are the cases that
  matter.
- **Fernet, `django-cryptography`, `django-fernet-fields`.** The wrappers are
  effectively unmaintained against Django 5.x, and Fernet is AES-CBC+HMAC with
  **no AAD**, so we would lose the row binding above.

### 2. Lockout counters: a dedicated table

Table `signin_throttle`, one row per normalized email, holding
`failure_count`, `window_started_at` and `locked_until`. Each attempt runs in
one transaction against `SELECT … FOR UPDATE` on that row.

This is a **fixed** window that resets once stale, not a true sliding window.
It satisfies the brief's edge case and AC-LO-5, and costs one row instead of
one row per attempt.

**Not the audit log.** Counting `signin_failed` rows is tempting, since
AC-LO-7 requires writing them anyway. But the audit log is append-only by
AC-AL-5, so the AC-LO-5 reset becomes a "failures since last success"
subquery — and the lock itself still needs mutable state somewhere. Mixing an
immutable evidence log with mutable control state compromises both. The
throttle row is control state; audit events remain the record.

**Not `django-axes`.** It brings its own middleware, signals and admin surface,
and its lockout semantics are configurable in ways that drift from the brief.
Roughly eighty lines we own and test directly against AC-LO-1…7 is less code
than the configuration we would otherwise have to get exactly right.

### 3. Client IP: walk `X-Forwarded-For` right to left

Never read `X-Forwarded-For[0]`. That is the attacker's field — clients send
whatever they like and the proxy appends.

The rule: walk the header **right to left**, discarding entries inside
`TRUSTED_PROXY_CIDRS`. The first entry that is not trusted is the client. If
the header is absent, or every entry is trusted, fall back to `REMOTE_ADDR`.

`TRUSTED_PROXY_CIDRS` is environment configuration, because the hop count
differs per environment — empty in local and test, so nothing trusts a
client-supplied header by default. Implemented once as
`alfulk.core.client_ip(request)`, never inline.

**Not `django-ipware`.** It can be configured to do the same thing, but its
default trusts the leftmost entry. A security control whose safe behavior
depends on remembering to override a default is the wrong shape.

Addresses are stored in a `GenericIPAddressField` (`inet`), full value, IPv4
and IPv6 both, with no truncation in increment 1.

## Consequences

### What the TOTP encryption actually buys

It defends against anything that yields database contents **without** the
application's environment: a dump, a backup, a replica, a SQL-injection read.

It does **not** defend against code execution on the application host, which
holds the key by definition. Worth stating plainly so nobody later reads
"encrypted at rest" as more than it is.

### Losing the key is worse than losing the database

`TOTP_SECRET_ENCRYPTION_KEYS` must be in **key escrow**, separately from the
backups it protects. If it is lost, every user loses their second factor, with
recovery codes as the only path back. A restore drill that does not prove the
escrowed copy works has not proved recovery — see F6.

### Costs we accept

- A new per-environment secret, with an escrow requirement and a rotation
  command to build and maintain.
- A sign-in-path transaction and row lock on `signin_throttle`. Fine at our
  scale, on a path that runs at human speed.
- One row per distinct attempted email, including bot traffic, pruned by a
  management command on a host cron.
- `TRUSTED_PROXY_CIDRS` must be kept truthful as the topology changes. If it
  is ever wrong, audit IPs become forgeable — which is the failure this ADR
  exists to prevent, so it belongs in the deployment checklist rather than in
  someone's memory.

### Dependency on the proxy configuration

The trusted-hop assumption is only true if the application binds exclusively to
the private network and is never directly reachable. Caddy must also **set**,
not append, `X-Forwarded-Proto`, or Django believes it is on plain HTTP and
refuses to set `Secure` cookies — failing AC-SI-3 in a way that looks like an
application bug. Both are requirements on F2, recorded there.
