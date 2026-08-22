"""The real external action taken outside Notion once a request is
approved (auto or human): notify procurement by email.

If SMTP isn't configured, runs in DEV_MODE and records exactly what would
have been sent - it never claims an email was sent when it wasn't.
"""
import logging
import smtplib
import uuid
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DEV_MODE = not (settings.smtp_host and settings.smtp_username)


class ActionError(Exception):
    pass


def send_procurement_notification(req, approved_by: str = "Auto-Processing") -> str:
    """Sends the approved-purchase email. Returns an external_action_id.

    Raises ActionError on real failure so the caller marks the request
    ACTION_FAILED rather than COMPLETED.
    """
    subject = f"Approved Purchase Request {req.id}"
    body = (
        f"Employee: {req.employee_name}\n"
        f"Department: {req.department}\n"
        f"Item: {req.quantity}x {req.item}\n"
        f"Estimated Amount: {req.currency} {req.estimated_amount:,.0f}\n"
        f"Approved By: {approved_by}\n"
        f"Request ID: {req.id}\n"
    )

    if DEV_MODE:
        action_id = f"dev-email-{uuid.uuid4().hex[:8]}"
        logger.info(
            "[DEV_MODE] SMTP not configured - NOT sending a real email. "
            "Would send:\nSubject: %s\n%s", subject, body,
        )
        return action_id

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = settings.procurement_email

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)

        return f"email-{uuid.uuid4().hex[:8]}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send procurement email for %s", req.id)
        raise ActionError(str(exc)) from exc
