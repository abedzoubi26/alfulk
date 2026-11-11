# Architecture Decision Records

An ADR records one architecturally significant decision: the context that forced
it, the decision itself, and the consequences we accept by taking it.

## Index

| ADR | Title | Status |
| --- | --- | --- |
| [0000](0000-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0001](0001-technology-stack.md) | Technology stack for Alfulk | Accepted, superseded in part by [0005](0005-credential-storage-and-client-ip.md) |
| [0002](0002-hosting-provider.md) | Hosting provider | Proposed |
| [0003](0003-environments.md) | Environments: preview, staging, production | Accepted |
| [0004](0004-ci-cd-and-branching.md) | CI/CD, branching and review gates | Accepted |
| [0005](0005-credential-storage-and-client-ip.md) | Credential storage at rest, and resolving the client IP | Accepted |

## Status values

- **Proposed** — written, not yet agreed. Needs a decision from the board or the CTO.
- **Accepted** — in force. Build against it.
- **Superseded by ADR-NNNN** — replaced. Keep the file; never delete history.
- **Superseded in part by ADR-NNNN** — still in force, except for one part that
  a later record replaces. The later record names exactly which part in its
  `Supersedes` line, and the amended record carries a pointer at that spot.
- **Deprecated** — no longer applies and nothing replaced it.

## Writing a new ADR

1. Copy the structure of an existing record.
2. Number it with the next free four-digit number.
3. Name the file `NNNN-kebab-case-title.md`.
4. Open it in a pull request; the ADR is agreed when the pull request merges.
5. Add it to the index above in the same pull request.

Never edit an accepted ADR to change its decision. Write a new ADR that
supersedes it, and mark the old one `Superseded by ADR-NNNN`. If only part of a
record is replaced, the new ADR names that part in its `Supersedes` line and the
old one gets a `Superseded in part by ADR-NNNN` pointer at that spot — the rest
of it stays in force. A record that quietly contradicts an accepted one is the
failure this process exists to prevent, and it is not hypothetical: ADR-0001 and
ADR-0005 gave opposite instructions on TOTP secret encryption for several hours
before anyone noticed.
