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
procureflow_page_url = ""

DEV_MODE = settings.demo_mode or not settings.notion_token

if not DEV_MODE:
    from notion_client import Client
    from notion_client.errors import APIResponseError

    _client = Client(auth=settings.notion_token, notion_version=settings.notion_api_version)
else:
    _client = None
    APIResponseError = Exception  # type: ignore
    logger.warning(
        "NOTION_TOKEN or database IDs not configured - running Notion service "
        "in DEV_MODE (actions are logged locally, not sent to Notion)."
    )


class NotionServiceError(Exception):
    pass


def notion_status(status: str) -> str:
    """Translate local enum values to the select values created in Notion."""
    return {
        "RECEIVED": "Received",
        "PROCESSING": "Processing",
        "PENDING_APPROVAL": "Pending Approval",
        "APPROVED": "Approved",
        "REJECTED": "Rejected",
        "AUTO_PROCESSED": "Auto-Processed",
        "COMPLETED": "Completed",
        "FAILED": "Failed",
        "ACTION_FAILED": "Action Failed",
        "NEEDS_REVIEW": "Needs Review",
        "PENDING": "Pending",
        "OVERRIDDEN": "Override",
    }.get(status, status)


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


def _email(text: str) -> dict:
    return {"email": text} if text else {"email": None}


def _url(text: str) -> dict:
    return {"url": text} if text else {"url": None}


def _date(value: str) -> dict:
    return {"date": {"start": value}} if value else {"date": None}


def _select(name: str) -> dict:
    return {"select": {"name": name}} if name else {"select": None}


def _number(value) -> dict:
    return {"number": value}


def _checkbox(value: bool) -> dict:
    return {"checkbox": bool(value)}


def create_purchase_request_page(req) -> str:
    """Create the master record in the Purchase Requests DB."""
    properties = {
        "Name": _title(req.id),
        "Request ID": _rich_text(req.id),
        "Employee Name": _rich_text(req.employee_name),
        "Employee Email": _email(req.employee_email),
        "Department": _rich_text(req.department),
        "Original Request": _rich_text(req.request_text),
        "Item": _rich_text(req.item or "Unspecified"),
        "Category": _select(req.category or "Other"),
        "Quantity": _number(req.quantity),
        "Estimated Amount": _number(req.estimated_amount),
        "Currency": _select(req.currency or "INR"),
        "Priority": _select(req.priority or "Medium"),
        "Risk Level": _select(req.risk_level or "Low"),
        "AI Confidence": _number(req.confidence),
        "Status": _select(notion_status(req.status.value if hasattr(req.status, "value") else req.status)),
        "Approval Required": _checkbox(bool(req.approval_required)),
        "Created At": _date(req.created_at.isoformat() if req.created_at else ""),
        "Updated At": _date(req.updated_at.isoformat() if req.updated_at else ""),
    }
    return _create_page(settings.notion_requests_database_id, properties)


def update_purchase_request_status(page_id: str, status: str, approver: str = "") -> None:
    properties = {"Status": _select(notion_status(status))}
    if approver:
        properties["Approver"] = _rich_text(approver)
    _update_page(page_id, properties)


def create_approval_item(req) -> str:
    """Create a row in the Approval Queue - only for requests needing a human."""
    properties = {
        "Name": _title(req.id),
        "Request ID": _rich_text(req.id),
        "Employee": _rich_text(req.employee_name),
        "Employee Email": _email(req.employee_email),
        "Department": _rich_text(req.department),
        "Purchase": _rich_text(f"{req.quantity}x {req.item}"),
        "Quantity": _number(req.quantity),
        "Amount": _number(req.estimated_amount),
        "Risk": _select(req.risk_level or "Unknown"),
        "AI Confidence": _number(req.confidence),
        "Decision Reason": _rich_text(req.ai_reasoning or "Review and approve/reject/override"),
        "Status": _select(notion_status("PENDING")),
        "Created At": _date(req.created_at.isoformat() if req.created_at else ""),
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


def _notion_error_message(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if "unauthorized" in lowered or "forbidden" in lowered:
        return "Notion integration failed: share the parent page and databases with your ProcureFlow integration."
    if "object_not_found" in lowered or "not found" in lowered:
        return "Notion integration failed: verify the parent page and database IDs in .env."
    return f"Notion integration failed: {message}"


def integration_status() -> dict:
    """Return safe diagnostics without exposing tokens or API exceptions."""
    result = {
        "mode": "DEMO" if DEV_MODE else "REAL",
        "token_configured": bool(settings.notion_token),
        "connected": False,
        "database_access": False,
        "schema_valid": False,
        "missing_properties": [],
        "invalid_properties": [],
        "databases": {
            "purchase_requests": {"exists": False, "schema_valid": False},
            "approval_queue": {"exists": False, "schema_valid": False},
            "run_log": {"exists": False, "schema_valid": False},
        },
        "message": "Notion is not configured; using local demo mode." if DEV_MODE else "",
        "procureflow_url": procureflow_page_url,
    }
    if DEV_MODE:
        return result
    try:
        _client.users.me()
        result["connected"] = True
        schemas = {
            "purchase_requests": settings.notion_requests_database_id,
            "approval_queue": settings.notion_approvals_database_id,
            "run_log": settings.notion_run_log_database_id,
        }
        required = {
            "purchase_requests": {"Request ID", "Status", "Employee", "Department"},
            "approval_queue": {"Request ID", "Status", "Employee", "Purchase"},
            "run_log": {"Run ID", "Request ID", "Event", "Status"},
        }
        for name, database_id in schemas.items():
            if not database_id:
                result["missing_properties"].append(f"{name}: database is not configured")
                continue
            properties = _client.databases.retrieve(database_id=database_id).get("properties", {})
            result["databases"][name]["exists"] = True
            result["databases"][name]["schema_valid"] = all(prop in properties for prop in required[name])
            result["missing_properties"].extend(
                f"{name}: {prop}" for prop in required[name] if prop not in properties
            )
        result["database_access"] = True
        result["schema_valid"] = not result["missing_properties"]
        if not result["schema_valid"]:
            result["message"] = "Notion is connected, but one or more database properties are missing."
        return result
    except Exception as exc:  # noqa: BLE001
        result["message"] = _notion_error_message(exc)
        result["error_type"] = type(exc).__name__
        return result


def validate_schema() -> dict:
    return integration_status()


def _plain_title(properties: dict) -> str:
    for key in ("title", "rich_text"):
        values = properties.get(key, [])
        if values:
            return "".join(value.get("plain_text", "") for value in values)
    return ""


def _object_title(result: dict) -> str:
    if result.get("object") == "database":
        title = result.get("title", [])
        return "".join(item.get("plain_text", "") for item in title)
    return _plain_title(result.get("properties", {}).get("title", {})) or _plain_title(result.get("properties", {}).get("Name", {}))


def _search_exact(title: str, object_type: str) -> dict | None:
    results = _client.search(query=title, filter={"property": "object", "value": object_type}).get("results", [])
    for result in results:
        if _object_title(result) == title:
            return result
    return None


def _database_schema(title: str) -> dict:
    common = {
        "Request ID": {"rich_text": {}},
    }
    if title.endswith("Purchase Requests"):
        return {
            "Name": {"title": {}}, **common, "Status": {"select": {"options": [{"name": x} for x in ("Received", "Processing", "Pending Approval", "Approved", "Rejected", "Auto-Processed", "Completed", "Failed", "Action Failed", "Needs Review")]}}, "Employee Name": {"rich_text": {}},
            "Employee Email": {"email": {}}, "Department": {"rich_text": {}},
            "Original Request": {"rich_text": {}}, "Item": {"rich_text": {}},
            "Quantity": {"number": {}}, "Category": {"select": {"options": []}},
            "Estimated Amount": {"number": {}}, "Currency": {"select": {"options": [{"name": "INR"}]}},
            "Priority": {"select": {"options": [{"name": x} for x in ("Low", "Medium", "High", "Critical")]}},
            "Risk Level": {"select": {"options": [{"name": x} for x in ("Low", "Medium", "High")]}},
            "AI Confidence": {"number": {}}, "Approval Required": {"checkbox": {}},
            "Created At": {"date": {}}, "Updated At": {"date": {}}, "Notion Request URL": {"url": {}},
        }
    if title.endswith("Approval Queue"):
        return {
            "Name": {"title": {}}, **common, "Status": {"select": {"options": [{"name": x} for x in ("Pending", "Approved", "Rejected", "Override", "Blocked")]}}, "Employee": {"rich_text": {}},
            "Employee Email": {"email": {}}, "Department": {"rich_text": {}}, "Purchase": {"rich_text": {}},
            "Quantity": {"number": {}}, "Amount": {"number": {}},
            "Risk": {"select": {"options": [{"name": x} for x in ("Low", "Medium", "High")]}},
            "AI Confidence": {"number": {}}, "Approver": {"rich_text": {}},
            "Decision Reason": {"rich_text": {}}, "Decision At": {"date": {}}, "Created At": {"date": {}},
            "ProcureFlow Request URL": {"url": {}},
        }
    return {
        "Name": {"title": {}}, "Event ID": {"rich_text": {}}, "Request ID": {"rich_text": {}},
        "Event Type": {"select": {"options": []}}, "Actor": {"rich_text": {}},
        "Status": {"select": {"options": [{"name": x} for x in ("SUCCESS", "FAILURE", "INFO")]}}, "Reason": {"rich_text": {}}, "Error": {"rich_text": {}},
        "Timestamp": {"date": {}},
    }


def _create_database(parent_page_id: str, title: str) -> dict:
    return _client.databases.create(
        parent={"page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": title}}],
        properties=_database_schema(title),
    )


def setup_procureflow(parent_page_id: str) -> dict:
    """Discover or create the ProcureFlow hierarchy without touching other pages."""
    if DEV_MODE:
        raise NotionServiceError("Real Notion setup requires NOTION_TOKEN and NOTION_PARENT_PAGE_ID.")
    try:
        _client.pages.retrieve(page_id=parent_page_id)
        page = _search_exact("ProcureFlow", "page")
        if not page:
            page = _client.pages.create(parent={"page_id": parent_page_id}, properties={"title": _title("ProcureFlow")})
        databases = {}
        for suffix, key in (("Purchase Requests", "purchase_requests_database"), ("Approval Queue", "approval_queue_database"), ("Run Log", "run_log_database")):
            title = f"ProcureFlow - {suffix}"
            database = _search_exact(title, "database")
            if not database:
                database = _create_database(page["id"], title)
            databases[key] = {"id": database["id"], "url": database.get("url", "")}
        global procureflow_page_url
        settings.notion_requests_database_id = databases["purchase_requests_database"]["id"]
        settings.notion_approvals_database_id = databases["approval_queue_database"]["id"]
        settings.notion_run_log_database_id = databases["run_log_database"]["id"]
        procureflow_page_url = page.get("url", "")
        return {
            "success": True, "workspace": "Game Player's Space", "procureflow_page": page["id"],
            "procureflow_url": page.get("url", ""), **databases,
        }
    except Exception as exc:  # noqa: BLE001
        raise NotionServiceError(_notion_error_message(exc)) from exc
