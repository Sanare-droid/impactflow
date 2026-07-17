"""Branded billing lifecycle emails."""

from __future__ import annotations

from typing import Any, Optional

from app.core.config import settings
from app.services.mailer import send_email


def _brand_wrap(title: str, body_html: str) -> str:
    frontend = (settings.frontend_url or "").rstrip("/")
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#F7F4EC;font-family:Georgia,'Times New Roman',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F4EC;padding:32px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#FFFEFB;border:1px solid #E8E2D6;border-radius:12px;overflow:hidden;">
        <tr><td style="background:#16324F;color:#FFFEFB;padding:20px 28px;font-size:20px;font-weight:600;">ImpactFlow</td></tr>
        <tr><td style="padding:28px;color:#3F3A34;">
          <h1 style="margin:0 0 12px;font-size:22px;color:#16324F;">{title}</h1>
          {body_html}
          <p style="margin:24px 0 0;font-size:13px;color:#7A7268;">
            Manage billing at <a href="{frontend}/app/billing" style="color:#0F766E;">{frontend}/app/billing</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def send_billing_email(
    *,
    to: str,
    subject: str,
    title: str,
    paragraphs: list[str],
    cta_label: Optional[str] = None,
    cta_url: Optional[str] = None,
) -> dict[str, Any]:
    parts = "".join(f"<p style='margin:0 0 12px;line-height:1.55;'>{p}</p>" for p in paragraphs)
    if cta_label and cta_url:
        parts += (
            f"<p style='margin:20px 0 0;'><a href='{cta_url}' "
            f"style='display:inline-block;background:#1B2A4A;color:#fff;text-decoration:none;"
            f"padding:10px 18px;border-radius:8px;font-size:14px;'>{cta_label}</a></p>"
        )
    html = _brand_wrap(title, parts)
    text = "\n\n".join(paragraphs)
    if cta_url:
        text += f"\n\n{cta_label or 'Open'}: {cta_url}"
    return await send_email(to=to, subject=subject, body=text, html=html)


async def trial_started(to: str, *, org_name: str, days: int = 14) -> dict[str, Any]:
    frontend = (settings.frontend_url or "").rstrip("/")
    return await send_billing_email(
        to=to,
        subject="Your ImpactFlow free trial has started",
        title="Welcome — trial started",
        paragraphs=[
            f"Hi — {org_name} is on a {days}-day Free Trial.",
            "Invite your team, publish a survey, and explore field sync before your trial ends.",
        ],
        cta_label="Open workspace",
        cta_url=f"{frontend}/app/onboarding",
    )


async def trial_ending(to: str, *, org_name: str, days_left: int) -> dict[str, Any]:
    frontend = (settings.frontend_url or "").rstrip("/")
    return await send_billing_email(
        to=to,
        subject=f"Your ImpactFlow trial ends in {days_left} day{'s' if days_left != 1 else ''}",
        title="Trial ending soon",
        paragraphs=[
            f"{org_name}'s free trial ends in {days_left} day{'s' if days_left != 1 else ''}.",
            "Upgrade now to keep surveys, mobile sync, and your program data fully writable.",
        ],
        cta_label="Upgrade plan",
        cta_url=f"{frontend}/app/billing",
    )


async def payment_successful(
    to: str, *, plan_name: str, amount: str, reference: str
) -> dict[str, Any]:
    frontend = (settings.frontend_url or "").rstrip("/")
    return await send_billing_email(
        to=to,
        subject="Payment successful — ImpactFlow",
        title="Payment successful",
        paragraphs=[
            f"Your payment for the {plan_name} plan was successful.",
            f"Amount: {amount}. Reference: {reference}.",
        ],
        cta_label="View billing",
        cta_url=f"{frontend}/app/billing",
    )


async def invoice_email(
    to: str, *, invoice_number: str, amount: str, plan_name: str
) -> dict[str, Any]:
    frontend = (settings.frontend_url or "").rstrip("/")
    return await send_billing_email(
        to=to,
        subject=f"Invoice {invoice_number} — ImpactFlow",
        title="Your invoice",
        paragraphs=[
            f"Invoice {invoice_number} for {plan_name}.",
            f"Amount: {amount}.",
        ],
        cta_label="View invoices",
        cta_url=f"{frontend}/app/billing",
    )


async def payment_failed(to: str, *, org_name: str) -> dict[str, Any]:
    frontend = (settings.frontend_url or "").rstrip("/")
    return await send_billing_email(
        to=to,
        subject="Payment failed — action needed",
        title="Payment failed",
        paragraphs=[
            f"We could not renew billing for {org_name}.",
            "A 7-day grace period has started. Update payment to avoid read-only mode.",
        ],
        cta_label="Fix billing",
        cta_url=f"{frontend}/app/billing",
    )


async def subscription_cancelled(to: str, *, org_name: str) -> dict[str, Any]:
    frontend = (settings.frontend_url or "").rstrip("/")
    return await send_billing_email(
        to=to,
        subject="Subscription cancelled",
        title="Subscription cancelled",
        paragraphs=[
            f"Billing for {org_name} has been cancelled.",
            "You can reactivate anytime from the billing page.",
        ],
        cta_label="Reactivate",
        cta_url=f"{frontend}/app/billing",
    )


async def upgrade_confirmation(to: str, *, plan_name: str) -> dict[str, Any]:
    frontend = (settings.frontend_url or "").rstrip("/")
    return await send_billing_email(
        to=to,
        subject=f"Upgraded to {plan_name}",
        title="Plan upgraded",
        paragraphs=[f"You are now on the {plan_name} plan. New features are available immediately."],
        cta_label="Open workspace",
        cta_url=f"{frontend}/app",
    )


async def renewal_reminder(to: str, *, plan_name: str, renew_at: str) -> dict[str, Any]:
    frontend = (settings.frontend_url or "").rstrip("/")
    return await send_billing_email(
        to=to,
        subject="Upcoming renewal — ImpactFlow",
        title="Renewal reminder",
        paragraphs=[
            f"Your {plan_name} subscription renews on {renew_at}.",
            "No action is needed if your payment method is up to date.",
        ],
        cta_label="Manage billing",
        cta_url=f"{frontend}/app/billing",
    )


async def email_verification(to: str, *, verify_url: str) -> dict[str, Any]:
    return await send_billing_email(
        to=to,
        subject="Verify your ImpactFlow email",
        title="Verify your email",
        paragraphs=[
            "Confirm your email to finish setting up your organization workspace.",
        ],
        cta_label="Verify email",
        cta_url=verify_url,
    )
