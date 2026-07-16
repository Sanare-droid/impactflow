"""Branded HTML + plain-text email bodies for transactional mail."""

from __future__ import annotations

from html import escape


def _layout(*, title: str, preheader: str, inner_html: str) -> str:
    """Table-based layout for broad email-client support."""
    t = escape(title)
    p = escape(preheader)
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{t}</title>
</head>
<body style="margin:0;padding:0;background:#F4F1EA;font-family:Georgia,'Times New Roman',serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{p}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#F4F1EA;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="560" cellspacing="0" cellpadding="0" style="max-width:560px;width:100%;background:#FFFEFB;border:1px solid #E8E2D6;">
          <tr>
            <td style="background:#16324F;padding:28px 32px;">
              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:0.14em;text-transform:uppercase;color:#A8C5A0;">ImpactFlow</p>
              <h1 style="margin:10px 0 0;font-size:26px;line-height:1.25;font-weight:600;color:#FFFFFF;">{t}</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;color:#3F3A34;">
              {inner_html}
            </td>
          </tr>
          <tr>
            <td style="padding:18px 32px 28px;border-top:1px solid #E8E2D6;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.5;color:#8A8278;">
              Sent by ImpactFlow · If you did not expect this message, you can ignore it.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _button(*, href: str, label: str) -> str:
    return (
        f'<a href="{escape(href)}" '
        'style="display:inline-block;background:#1B2A4A;color:#FFFFFF;text-decoration:none;'
        "font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:600;"
        'padding:12px 22px;border-radius:6px;">'
        f"{escape(label)}</a>"
    )


def invite_new_user(
    *,
    email: str,
    temporary_password: str,
    login_url: str,
    first_name: str = "",
) -> tuple[str, str, str]:
    """Returns (subject, plain_text, html)."""
    name = (first_name or "").strip() or "there"
    subject = "Your ImpactFlow invitation"
    plain = (
        f"Hi {name},\n\n"
        f"You have been invited to ImpactFlow.\n\n"
        f"Email: {email}\n"
        f"Temporary password: {temporary_password}\n"
        f"Sign in: {login_url}\n\n"
        f"You will be asked to change your password after login.\n"
    )
    inner = f"""
      <p style="margin:0 0 16px;">Hi {escape(name)},</p>
      <p style="margin:0 0 16px;">You have been invited to <strong>ImpactFlow</strong>. Use the details below to sign in for the first time.</p>
      <table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;margin:0 0 20px;background:#F7F4EC;border:1px solid #E8E2D6;">
        <tr><td style="padding:14px 16px;font-size:13px;color:#5A534B;">Email</td>
            <td style="padding:14px 16px;font-size:14px;color:#16324F;"><strong>{escape(email)}</strong></td></tr>
        <tr><td style="padding:14px 16px;font-size:13px;color:#5A534B;border-top:1px solid #E8E2D6;">Temporary password</td>
            <td style="padding:14px 16px;font-size:14px;color:#16324F;border-top:1px solid #E8E2D6;font-family:Consolas,Monaco,monospace;">{escape(temporary_password)}</td></tr>
      </table>
      <p style="margin:0 0 22px;">{_button(href=login_url, label="Sign in to ImpactFlow")}</p>
      <p style="margin:0;font-size:13px;color:#7A7268;">You will be asked to change your password after login.</p>
    """
    return subject, plain, _layout(title="You're invited", preheader="Sign in to your ImpactFlow workspace", inner_html=inner)


def invite_existing_user(*, login_url: str, first_name: str = "") -> tuple[str, str, str]:
    name = (first_name or "").strip() or "there"
    subject = "You've been added to an ImpactFlow organization"
    plain = (
        f"Hi {name},\n\n"
        f"You have been added to an organization on ImpactFlow.\n\n"
        f"Sign in with your existing account: {login_url}\n"
    )
    inner = f"""
      <p style="margin:0 0 16px;">Hi {escape(name)},</p>
      <p style="margin:0 0 22px;">You have been added to an organization on <strong>ImpactFlow</strong>. Sign in with your existing account to continue.</p>
      <p style="margin:0;">{_button(href=login_url, label="Open ImpactFlow")}</p>
    """
    return subject, plain, _layout(title="New organization access", preheader="You were added to a workspace", inner_html=inner)


def password_reset(*, reset_url: str, first_name: str = "") -> tuple[str, str, str]:
    name = (first_name or "").strip() or "there"
    subject = "Reset your ImpactFlow password"
    plain = (
        f"Hi {name},\n\n"
        f"Use this link to reset your password (expires in 1 hour):\n{reset_url}\n\n"
        f"If you did not request this, ignore this email.\n"
    )
    inner = f"""
      <p style="margin:0 0 16px;">Hi {escape(name)},</p>
      <p style="margin:0 0 22px;">We received a request to reset your ImpactFlow password. This link expires in <strong>1 hour</strong>.</p>
      <p style="margin:0 0 22px;">{_button(href=reset_url, label="Reset password")}</p>
      <p style="margin:0;font-size:13px;color:#7A7268;">If you did not request this, you can safely ignore this email.</p>
      <p style="margin:16px 0 0;font-size:12px;color:#8A8278;word-break:break-all;">Or paste this link into your browser:<br />{escape(reset_url)}</p>
    """
    return subject, plain, _layout(title="Password reset", preheader="Reset your ImpactFlow password", inner_html=inner)
