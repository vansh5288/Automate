"""Notion integration.

Creates/updates rows in the Purchase Requests, Approval Queue, and Run Log
databases, and reads back human decisions from the Approval Queue.

If NOTION_TOKEN / database IDs aren't configured, this module runs in a
clearly-labeled DEV_MODE that logs what *would* have been sent to Notion
instead of silently pretending to succeed - so the rest of the pipeline
can still be exercised locally.
"""
import logging
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DEV_MODE = not (settings.notion_token and settings.notion_requests_database_id)

if not DEV_MODE:
    from notion_client import Client
    from notion_client.errors import APIResponseError

    _client = Client(auth=settings.notion_token)
else:
    _client = None
    APIResponseError = Exception  # type: ignore
    logger.warning(
        "NOTION_TOKEN or database IDs not configured - running Notion service "
        "in DEV_MODE (actions are logged locally, not sent to Notion)."
    )


class NotionServiceError(Exception):
    pass


def _retryable():
    return retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(APIResponseError),
    )


@_retryable()
def _create_page(database_id: str, properties: dict) -> str:
    if DEV_MODE:
        logger.info("[DEV_MODE] Would create Notion page in %s: %s", database_id, properties)
        return f"dev-page-{abs(hash(str(properties))) % 100000}"
    page = _client.pages.create(parent={"database_id": database_id}, properties=properties)
    return page["id"]


@_retryable()
def _update_page(page_id: str, properties: dict) -> None:
    if DEV_MODE:
        logger.info("[DEV_MODE] Would update Notion page %s: %s", page_id, properties)
        return
    _client.pages.update(page_id=page_id, properties=properties)


@_retryable()
def _query_database(database_id: str, filter_: Optional[dict] = None) -> list:
    if DEV_MODE:
        return []
    kwargs = {"database_id": database_id}
    if filter_:
        kwargs["filter"] = filter_
    return _client.databases.query(**kwargs)["results"]


def _title(text: str) -> dict:
    return {"title": [{"text": {"content": text[:2000]}}]}


def _rich_text(text: str) -> dict:
    return {"rich_text": [{"text": {"content": text[:2000]}}]}


def _select(name: str) -> dict:
    return {"select": {"name": name}} if name else {"select": None}


def _number(value) -> dict:
    return {"number": value}


def _checkbox(value: bool) -> dict:
    return {"checkbox": bool(value)}


def create_purchase_request_page(req) -> str:
    """Create the master record in the Purchase Requests DB."""
    properties = {
        "Request ID": _title(req.id),
        "Employee": _rich_text(req.employee_name),
        "Email": _rich_text(req.employee_email),
        "Department": _select(req.department),
        "Request": _rich_text(req.request_text),
        "Category": _select(req.category or "Other"),
        "Quantity": _number(req.quantity),
        "Estimated Amount": _number(req.estimated_amount),
        "Risk": _select(req.risk_level or "Unknown"),
        "Priority": _select(req.priority or "Medium"),
        "AI Confidence": _number(req.confidence),
        "Status": _select(req.status.value if hasattr(req.status, "value") else req.status),
        "Approval Required": _checkbox(bool(req.approval_required)),
    }
    return _create_page(settings.notion_requests_database_id, properties)


def update_purchase_request_status(page_id: str, status: str, approver: str = "") -> None:
    properties = {"Status": _select(status)}
    if approver:
        properties["Approver"] = _rich_text(approver)
    _update_page(page_id, properties)


def create_approval_item(req) -> str:
    """Create a row in the Approval Queue - only for requests needing a human."""
    properties = {
        "Request ID": _title(req.id),
        "Employee": _rich_text(req.employee_name),
        "Purchase": _rich_text(f"{req.quantity}x {req.item}"),
        "Amount": _number(req.estimated_amount),
        "Risk": _select(req.risk_level or "Unknown"),
        "AI reasoning summary": _rich_text(req.ai_reasoning or ""),
        "Recommended action": _rich_text("Review and approve/reject/override"),
        "Status": _select("Pending"),
    }
    return _create_page(settings.notion_approvals_database_id, properties)


def get_pending_approval_decisions() -> list:
    """Poll the Approval Queue for rows a human has moved out of Pending."""
    if DEV_MODE:
        return []
    filter_ = {"property": "Status", "select": {"does_not_equal": "Pending"}}
    return _query_database(settings.notion_approvals_database_id, filter_)


def create_run_log_entry(log) -> str:
    properties = {
        "Run ID": _title(log.run_id),
        "Request ID": _rich_text(log.request_id),
        "Event": _select(log.event),
        "Status": _select(log.status),
        "Action": _rich_text(log.action or ""),
        "Actor": _rich_text(log.actor or "system"),
        "Reason": _rich_text(log.reason or ""),
        "Error": _rich_text(log.error or ""),
        "External Action ID": _rich_text(log.external_action_id or ""),
    }
    return _create_page(settings.notion_run_log_database_id, properties)
