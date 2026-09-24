from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.settings import Settings

logger = logging.getLogger(__name__)


def send_password_reset_otp(settings: Settings, recipient: str, otp: str) -> None:
    """Send a one-time password through Gmail SMTP over implicit TLS."""
    if not _is_configured(settings):
        logger.warning("Password-reset email was not sent: SMTP is not configured.")
        return

    message = EmailMessage()
    message["Subject"] = "Mã đặt lại mật khẩu ITMS"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "Mã OTP đặt lại mật khẩu ITMS của bạn là: "
        f"{otp}\n\nMã có hiệu lực trong 30 phút. Không chia sẻ mã này với bất kỳ ai."
    )
    try:
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, context=ssl.create_default_context(), timeout=10
        ) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Password-reset email could not be sent.")


def _is_configured(settings: Settings) -> bool:
    return bool(settings.smtp_username and settings.smtp_password and settings.smtp_from_email)
