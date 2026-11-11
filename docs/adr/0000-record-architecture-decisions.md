# ADR-0000: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** CTO
- **Supersedes:** —

## Context

Alfulk is built incrementally by several engineers across six modules
(M0 Foundations → M1 Identity & Sign-in → M2 Admin & Orgs → M3 OIDC provider →
M4 Drive → M5 Mail). Decisions taken in M0 — the web framework, the password
hash, the hosting provider — constrain every module after it, and the people
implementing M4 will not be in the room when M0 is decided.

Undocumented decisions get re-litigated, quietly reversed, or worked around.
That is expensive in a security-sensitive product where "why is it done this
way" usually has a real answer.

## Decision

We keep Architecture Decision Records in `docs/adr/`, one Markdown file per
decision, numbered sequentially, committed through the normal pull request
flow.

An ADR is required for a decision that is costly to reverse: a runtime
dependency we build on, a data store, a hosting or network boundary, an
authentication or cryptographic mechanism, or a change to how code reaches
production. Ordinary implementation choices inside a single module do not need
one.

Each record states context, the decision, the alternatives considered and why
they lost, and the consequences we accept.

## Alternatives considered

- **A wiki or an issue tracker.** Rejected: decisions drift out of sync with
  the code and are not reviewable alongside the change that implements them.
- **Nothing — rely on code review and memory.** Rejected: reviewers rotate, and
  agents working on later modules have no transcript of earlier reasoning.

## Consequences

- Every architecturally significant pull request carries an ADR, which adds
  review time up front.
- A new contributor can read `docs/adr/` top to bottom and understand the shape
  of the system before reading code.
- Reversing a decision is visible: it needs a new ADR, not a silent edit.
