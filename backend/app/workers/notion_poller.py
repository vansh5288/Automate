"""Background worker that polls the Notion Approval Queue for human
decisions and continues the workflow. Runs inside the FastAPI process on
a schedule (via asyncio task started at app startup) - the demo must not
depend on anyone manually running a script.
"""
import asyncio
import logging

from app.config import get_settings
from app.database import SessionLocal
from app.models.request import PurchaseRequest
from app.services import notion_service, procurement_service

logger = logging.getLogger(__name__)
settings = get_settings()

_STATUS_MAP = {
    "Approved": "APPROVED",
    "Rejected": "REJECTED",
    "Override": "OVERRIDDEN",
}


async def poll_loop():
    while True:
        try:
            await asyncio.to_thread(_poll_once)
        except Exception:  # noqa: BLE001
            logger.exception("Notion poll iteration failed")
        await asyncio.sleep(settings.notion_poll_interval_seconds)


def _poll_once():
    if notion_service.DEV_MODE:
        return  # nothing to poll against without a real Notion connection

    decisions = notion_service.get_pending_approval_decisions()
    if not decisions:
        return

    db = SessionLocal()
    try:
        for page in decisions:
            props = page.get("properties", {})
            request_id = _extract_title(props.get("Request ID"))
            status_name = _extract_select(props.get("Status"))
            approver = _extract_rich_text(props.get("Approver")) or "Notion Approver"

            if not request_id or status_name not in _STATUS_MAP:
                continue

            req = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
            if not req or req.status.value != "PENDING_APPROVAL":
                continue

            procurement_service.apply_human_decision(
                db, req, _STATUS_MAP[status_name], approver=approver,
            )
    finally:
        db.close()


def _extract_title(prop) -> str:
    if not prop or not prop.get("title"):
        return ""
    return "".join(t.get("plain_text", "") for t in prop["title"])


def _extract_select(prop) -> str:
    if not prop or not prop.get("select"):
        return ""
    return prop["select"].get("name", "")


def _extract_rich_text(prop) -> str:
    if not prop or not prop.get("rich_text"):
        return ""
    return "".join(t.get("plain_text", "") for t in prop["rich_text"])
