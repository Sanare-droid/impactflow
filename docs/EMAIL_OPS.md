# Email operations checklist (production)

Outbound invite and system mail use Resend (or SMTP) via `apps/api/app/services/mailer.py`.

## Railway environment

| Variable | Required | Notes |
|----------|----------|--------|
| `RESEND_API_KEY` | Yes (Resend path) | API key from Resend dashboard |
| `SMTP_FROM` | Yes | Must be an address on a **verified** domain in Resend (or your SMTP provider) |

## Verified From domain

1. In Resend (or your provider), add and verify the sending domain (DNS TXT/DKIM/SPF).
2. Set `SMTP_FROM` to something like `invites@yourdomain.org` — **not** `onboarding@resend.dev`.
3. Redeploy the API so the new env vars are loaded.
4. Invite a **non-owner** teammate and confirm that person receives the email (Resend’s test From only delivers to the account owner).

## Smoke test

1. Users → Invite with “Send invite email” checked.
2. UI should show an honest status (queued / sent / not configured / test From warning).
3. Invitee inbox (and spam) should contain the invite within a few minutes.

## If mail never arrives

- Confirm `SMTP_FROM` domain is verified and matches Resend.
- Check Railway logs for mailer errors / rate limits.
- Confirm the invitee email is correct and not blocked by org filters.
