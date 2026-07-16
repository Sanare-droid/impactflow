"""Email template smoke tests."""

from app.services import email_templates


def test_invite_new_user_includes_html_and_plain():
    subject, plain, html = email_templates.invite_new_user(
        email="a@example.com",
        temporary_password="TempPass1",
        login_url="https://impactflowai.netlify.app/login",
        first_name="Ada",
    )
    assert "invitation" in subject.lower() or "invited" in subject.lower()
    assert "TempPass1" in plain
    assert "TempPass1" in html
    assert "<!DOCTYPE html>" in html
    assert "Sign in to ImpactFlow" in html


def test_password_reset_includes_button_and_url():
    subject, plain, html = email_templates.password_reset(
        reset_url="https://impactflowai.netlify.app/reset-password?token=abc",
        first_name="Ada",
    )
    assert "Reset" in subject
    assert "token=abc" in plain
    assert "token=abc" in html
    assert "Reset password" in html


def test_workflow_message_styles_body_and_optional_link():
    subject, plain, html = email_templates.workflow_message(
        subject="Grant expiring",
        body="A grant is approaching its end date.\n\nPlease review.",
        link="https://impactflowai.netlify.app/app/grants",
        title="Action needed",
    )
    assert subject == "Grant expiring"
    assert "approaching" in plain
    assert "/app/grants" in plain
    assert "<!DOCTYPE html>" in html
    assert "Action needed" in html
    assert "Open in ImpactFlow" in html
    assert "Please review." in html
