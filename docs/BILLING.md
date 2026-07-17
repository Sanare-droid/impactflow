# Billing & subscriptions (ImpactFlow V2.1)

ImpactFlow billing extends Epic 7 — one `OrganizationSubscription` per organization, plans in `subscription_plans`, Paystack for paid checkout, and feature flags for module access.

## Happy path

1. Visitor opens `/pricing` (plans from `GET /api/v1/public/billing/plans`).
2. Registers at `/register` → org + admin + **Free Trial** subscription (`status=trialing`, 14 days).
3. Receives trial-started + email-verification messages.
4. Verifies email via `/verify-email?token=…`.
5. Onboards team; usage limited by trial plan.
6. Upgrades on `/app/billing` → Paystack checkout → server verify / webhook → `active` + invoice.
7. Renewals charge saved authorization via daily lifecycle job.

## Subscription statuses

`trialing` → `active` → (`past_due` → `grace` → `suspended`) | `cancelled` | `expired` | `renewing`

Grace lasts **7 days**. During grace/expired/suspended, creates (projects, surveys, AI, workflows, marketplace installs) return **402** `plan_limit` with `upgrade_url`.

## Key APIs

| Method | Path | Notes |
|--------|------|-------|
| GET | `/public/billing/plans` | Marketing catalog (KES) |
| GET | `/billing/subscription` | Current sub + days remaining |
| POST | `/billing/subscription/change` | Free internal; paid → Paystack |
| POST | `/billing/subscription/cancel` | Cancel at period end |
| GET | `/billing/usage` | Seats / projects / storage / AI / API |
| GET | `/billing/invoices` | Invoice history |
| POST | `/billing/paystack/initialize` | Start checkout |
| GET | `/billing/paystack/verify` | Server-side verify |
| POST | `/billing/paystack/webhook` | HMAC signature required |
| GET | `/platform/billing/analytics` | Super-admin MRR/ARR |
| POST | `/platform/billing/assign` | Manual Government / Enterprise |
| POST | `/internal/billing/run-lifecycle` | Cron (`X-Billing-Cron-Secret`) |

## Government

Hidden from public pricing (`contact_sales`). Self-checkout blocked. Platform admin assigns via `/platform/billing/assign`.

## Enforcement

- Seats: invite path
- Projects: create project
- Features: marketplace install, AI conversations, workflow runs, survey create
- Status: writable gates for grace/expired/suspended

## Docs

- [PRICING.md](./PRICING.md) — plan matrix
- [NETLIFY_RAILWAY.md](./NETLIFY_RAILWAY.md) — Paystack env + webhook
