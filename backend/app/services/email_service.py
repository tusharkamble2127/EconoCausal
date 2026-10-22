"""Email provider abstraction for password reset (and future transactional email)."""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailError(Exception):
    pass


def _send_via_brevo(to_email: str, reset_url: str) -> None:
    if not settings.brevo_api_key or not settings.brevo_template_id:
        raise EmailError("Brevo is not configured.")

    payload = {
        "to": [{"email": to_email}],
        "templateId": settings.brevo_template_id,
        "params": {
            "reset_url": reset_url,
        },
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": settings.brevo_api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code >= 400:
            logger.error("Brevo API error %s: %s", resp.status_code, resp.text)
            raise EmailError("Brevo API error.")
    except httpx.HTTPError as exc:
        logger.error("Brevo request failed: %s", exc)
        raise EmailError("Failed to send email via Brevo.") from exc


def _send_via_smtp(to_email: str, reset_url: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        logger.warning("SMTP not configured. Password reset email could not be sent in development mode.")
        return

    subject = "Reset your EconoCausal password"
    body = f"""You requested a password reset for your EconoCausal account.

Reset your password using the button below:
{reset_url}

This link expires in {settings.password_reset_expire_minutes} minutes.

If you did not request this reset, you can safely ignore this email.
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
    except Exception as exc:
        logger.error("Failed to send password reset email to %s", to_email)
        raise EmailError("Failed to send email.") from exc


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    if settings.brevo_api_key and settings.brevo_template_id:
        _send_via_brevo(to_email, reset_url)
    else:
        _send_via_smtp(to_email, reset_url)
