# Pricing (KES)

Plans are stored in the database (`subscription_plans`) and upserted from `PLAN_SEED` on API use. **Never hardcode plan prices in the frontend** — use `/api/v1/public/billing/plans` or `/pricing`.

| Plan | Monthly | Annual | Users | Projects | Storage | Trial |
|------|---------|--------|-------|----------|---------|-------|
| Community (`free`) | 0 | 0 | 5 | 2 | 1 GB | 14 days |
| Starter | 9,900 | 99,000 | 10 | 10 | 10 GB | — |
| Professional ⭐ | 24,900 | 249,000 | 50 | Unlimited | 50 GB | — |
| Enterprise | 79,900 | 799,000 | Unlimited | Unlimited | Unlimited | — |
| Government | Custom quotation | Custom quotation | Unlimited | Unlimited | Unlimited | Manual |

Currency: **KES**. Paystack charges the catalog amount directly (`PAYSTACK_CURRENCY=KES`).

## Feature highlights

- **Community (free trial):** surveys, mobile offline, beneficiaries, basic reports and dashboards — no AI, automation, marketplace, white-label, or API.
- **Starter:** 10 users — surveys, offline mobile, beneficiaries, reports, notifications, basic AI credits.
- **Professional (most popular):** 50 users, unlimited projects — AI Copilot, automation (workflows), executive dashboards, advanced reports, integrations, marketplace, white-label, API access. Expected default for donor-funded NGOs.
- **Enterprise:** unlimited users — dedicated onboarding, custom domains, SSO, priority support, custom integrations.
- **Government:** custom quotation; procurement-friendly manual billing with training, customization, and support. Assigned by Super Admin only.

## Implementation fees (one-time)

Billed separately from subscriptions; shown on `/pricing`.

| Service | Price |
|---------|-------|
| Onboarding | KES 30,000 |
| Training | KES 50,000 |
| Data migration | KES 100,000+ |
| Custom forms / workflows | Quote |
| API integrations | Quote |

## Changing prices

Update `PLAN_SEED` in `apps/api/app/services/enterprise.py` (or edit DB rows). `ensure_plans` **upserts** catalog fields so redeploys refresh pricing without manual SQL. Note: `workflows` (automation) is Professional+ — the `FLAG_SEED` rules must stay in sync with plan features.
