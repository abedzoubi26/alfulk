## What and why

<!-- What changes, and what problem it solves. Link the Paperclip issue. -->

Paperclip issue: ALF-

## How to verify

<!-- Steps a reviewer can follow, on the preview environment where relevant. -->

## Checklist

- [ ] Linked to its Paperclip issue above
- [ ] `ruff check .` and `ruff format --check .` pass locally
- [ ] Tests cover the new behaviour, including the failure paths
- [ ] Model changes include a migration, and it is backward-compatible with the currently deployed version
- [ ] No secret, key or credential is committed; new configuration is documented in `.env.example`
- [ ] An ADR is added or updated if this changes an architecturally significant decision

## Security notes

<!-- Required if this touches authentication, sessions, two-factor, recovery
     codes, permissions or anything cryptographic. Say what you changed and
     what you considered. Write "n/a" otherwise. -->
