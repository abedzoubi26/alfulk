# ADR-0002: Hosting provider

- **Status:** Proposed — needs board sign-off before any account is opened
- **Date:** 2026-11-11
- **Deciders:** CTO (recommendation), board (spend approval)
- **Supersedes:** —

> **No cloud resources have been created.** This record is a recommendation and
> a cost estimate only. Nothing is provisioned until the board approves the
> spend and the hosting account exists.

## Context

We have to choose where staging, production and per-pull-request preview
environments run. The choice is hard to reverse once it holds production user
accounts, so it is worth making against the *whole* roadmap rather than against
increment 1, which would run almost anywhere.

Three requirements come from later modules and should drive the decision now:

1. **M5 Mail needs to send and receive real email.** That means outbound TCP
   port 25, a static IPv4 address, and control over its reverse DNS (PTR)
   record. Without PTR and SPF/DKIM/DMARC alignment, mail from Alfulk lands in
   spam folders and the module is not shippable. **Most platform-as-a-service
   providers block port 25 outright and do not offer PTR control at all.**
   This single requirement eliminates a large part of the market.
2. **M4 Drive needs cheap, growing object storage** with an S3-compatible API
   and predictable egress pricing. Per-gigabyte egress billing on a file
   storage product is a cost risk that scales with success.
3. **Alfulk is self-hosted software.** Operators will deploy it on their own
   infrastructure. If our own reference deployment depends on one vendor's
   proprietary managed services, our deployment documentation stops matching
   what we actually run, and we will not notice when the self-hosted path
   breaks.

Against that, we are a small team. Ops burden is a real cost, and "we run our
own PostgreSQL" is a commitment to backups, restore drills, patching and
monitoring that somebody has to own.

## Decision

**Recommend Hetzner Cloud** (EU region — Falkenstein or Nuremberg) for preview,
staging and production, on plain virtual machines running Docker Compose, with
Hetzner Object Storage for backups and, later, Drive blobs.

We accept running PostgreSQL ourselves. Hetzner offers no managed database, and
that is the main cost of this recommendation. It is mitigated by making
backup-and-restore a first-class foundation task with a verified restore drill,
not an afterthought — see "Consequences".

### Topology

| Environment | Hosts | Notes |
| --- | --- | --- |
| Production | 1 app VM + 1 database VM, private network | Separated so the database is not exposed and the app can be rebuilt freely |
| Staging | 1 VM, app and database co-located | Same images and same deploy path as production, smaller |
| Preview | 1 shared VM | Each open pull request gets a Docker Compose stack and a `pr-<n>.preview.<domain>` hostname behind a reverse proxy; destroyed on merge or close |

Preview environments share one host rather than creating a VM per pull request.
Per-PR VMs would be cleaner in isolation terms but make cost unpredictable and
add a provisioning system we do not need yet.

### Estimated monthly cost

Indicative Hetzner list prices, EU region, excluding VAT. **These must be
re-checked at sign-up — they are from our research, not from a live quote.**

| Item | Spec | ~EUR/month |
| --- | --- | ---: |
| Production app server | CX32 — 4 vCPU, 8 GB RAM, 80 GB | 7.00 |
| Production database server | CX22 — 2 vCPU, 4 GB RAM, 40 GB | 4.00 |
| Staging server | CX22 — 2 vCPU, 4 GB RAM, 40 GB | 4.00 |
| Preview host | CX32 — 4 vCPU, 8 GB RAM, 80 GB | 7.00 |
| Automated server backups | +20% on three servers | 3.60 |
| Object storage (backups) | ~100 GB | 5.00 |
| Load balancer (production TLS, optional) | LB11 | 5.40 |
| Primary IPv4 addresses | 4 × ~0.60 | 2.40 |
| **Infrastructure subtotal** | | **~38 EUR** |
| Domain registration | ~15 EUR/year | 1.25 |
| **Total** | | **~39 EUR/month (~42 USD)** |

Dropping the load balancer — terminating TLS with Caddy on the app server
directly — brings this to roughly **34 EUR/month**. That is a reasonable
starting posture; add the load balancer when production needs a second app
server.

Costs that are **not** in this estimate and will arrive later:

- **M4 Drive storage**, which scales with real user data. Hetzner Object
  Storage is roughly 5 EUR per TB per month with ~1 EUR/TB egress. Budget for
  it when M4 is scoped, not now.
- **GitHub Actions minutes.** Free for a public repository. A private
  repository on the Free plan gets 2,000 minutes/month, which a Django test
  suite will not exhaust at this stage.
- **A transactional email provider** for sign-up and password-reset mail in
  M1. This is a separate, smaller decision from M5's full mail server; a free
  tier is sufficient for increment 1.

### Mail-specific caveat

Hetzner blocks outbound port 25 on new accounts and unblocks it on request
once the account has some history and a stated use case. **This request should
be made early — well before M5 — because the waiting period is the risk, not
the approval.** Hetzner does provide PTR record control through its console,
which is the part that cannot be worked around elsewhere.

## Alternatives considered

- **Fly.io.** Excellent developer experience, genuinely good per-PR preview
  story, global anycast. **Rejected: outbound port 25 is blocked with no
  exception path**, which makes M5 Mail impossible on it. Its PostgreSQL
  offering is also an unmanaged app template, so the database burden is not
  actually avoided.
- **Render.** Built-in preview environments and a genuinely managed PostgreSQL
  would save us real work. **Rejected on the same port 25 blocker**, plus
  no PTR control. Cost would also be higher: roughly 25 USD/month for web
  services plus 20+ USD/month for a production-grade managed database, before
  staging.
- **DigitalOcean.** Does everything we need technically — droplets, managed
  PostgreSQL at ~15 USD/month, Spaces object storage at 5 USD/month, and PTR
  records derived from the droplet name. The managed database is a real
  advantage over Hetzner. **Rejected on cost and on mail risk:** an equivalent
  topology lands around 75–85 USD/month, roughly twice Hetzner, and
  DigitalOcean is notably reluctant to unblock port 25 for new accounts.
  **This is the strongest runner-up.** If the board prefers to buy away the
  database operations burden, DigitalOcean is the one to switch to, and the
  decision should be taken now rather than after production data exists.
- **AWS or Google Cloud.** Rejected. Most expensive of the options at our
  scale, the largest operational surface to learn, port 25 is blocked by
  default on both, and building a Google replacement on Google's own platform
  is a poor look for a self-hosting product.
- **A single bare-metal server (Hetzner auction, OVH).** Cheapest per unit of
  compute and tempting. Rejected for now: no snapshot or rebuild story, slow
  hardware replacement, and a single machine with no isolation between
  preview, staging and production.

## Consequences

- **We own PostgreSQL operations.** Backups, encrypted off-host storage,
  monitoring, patching, and a *tested* restore are ours. A foundation task
  must deliver automated nightly backups to object storage and a documented,
  actually-executed restore drill before production holds a real account. This
  is the single largest risk this ADR accepts and it must not be deferred.
- Running on plain VMs with Docker Compose means the deployment we run is
  close to the deployment we document for self-hosters. That alignment is a
  benefit of this choice and we should keep it deliberately.
- Everything is in one EU region. There is no multi-region failover, and a
  Hetzner regional outage takes Alfulk down. Acceptable at this stage; revisit
  before any availability commitment is made to users.
- EU hosting is a good default for an identity product under GDPR, and keeps
  personal data in one jurisdiction.
- Hetzner's ecosystem is thinner than the hyperscalers': fewer managed
  services, a smaller Terraform/tooling community, less third-party
  integration. We trade convenience for cost and control.
- The port 25 unblock request is a dependency with an unknown lead time. It
  must be opened early so it is not on M5's critical path.
- Switching providers later is feasible — Docker Compose on VMs is close to
  portable — but migrating production identity data is never cheap. If
  DigitalOcean is preferred, choose it now.

## Open questions for the board

1. **Approve ~39 EUR/month** (or ~34 EUR/month without the load balancer) of
   recurring infrastructure spend?
2. **Hetzner, or DigitalOcean at roughly twice the price** to buy away the
   managed-database burden?
3. **Which domain** does Alfulk use? Staging and preview hostnames derive from
   it, and it needs registering before the first deployment.
