# Pricing (KES)

Plans are stored in the database (`subscription_plans`) and upserted from `PLAN_SEED` on API use. **Never hardcode prices in the frontend** — use `/api/v1/public/billing/plans` or `/pricing`.

| Plan | Monthly | Annual | Users | Projects | Storage | Trial |
|------|---------|--------|-------|----------|---------|-------|
| Free Trial (`free`) | 0 | 0 | 5 | 2 | 1 GB | 14 days |
| Starter | 7,500 | 75,000 | 10 | 10 | 10 GB | — |
| Professional | 20,000 | 200,000 | 50 | Unlimited | 50 GB | — |
| Enterprise | 60,000 | 600,000 | Unlimited | Unlimited | Unlimited | — |
| Government | Contact sales | Contact sales | Unlimited | Unlimited | Unlimited | Manual |

Currency: **KES**. Paystack charges the catalog amount directly (`PAYSTACK_CURRENCY=KES`).

## Feature highlights

- **Free Trial:** surveys, mobile, offline, basic dashboards — no AI Copilot, marketplace, white-label, API, advanced reports, executive analytics.
- **Starter:** + reports, notifications, basic workflows, basic AI credits.
- **Professional:** AI Copilot, executive dashboards, advanced reports, workflows, integrations, API, white-label, marketplace.
- **Enterprise:** everything + custom domain, SSO, SLA.
- **Government:** full platform; assigned by Super Admin only.

## Changing prices

Update `PLAN_SEED` in `apps/api/app/services/enterprise.py` (or edit DB rows). `ensure_plans` **upserts** catalog fields so redeploys refresh pricing without manual SQL.
