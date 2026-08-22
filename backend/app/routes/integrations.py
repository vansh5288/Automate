from fastapi import APIRouter

from app.config import get_settings
from app.services import notion_service

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status")
def integration_status():
    status = notion_service.integration_status()
    settings = get_settings()
    status["database"] = "OK"
    status["ai"] = "CONFIGURED" if settings.ai_provider == "mock" or settings.ai_api_key else "DEGRADED"
    status["smtp"] = "CONFIGURED" if settings.smtp_host and settings.smtp_username else "NOT_CONFIGURED"
    status["poller"] = "STOPPED" if notion_service.DEV_MODE else "RUNNING"
    return status


@router.post("/notion/validate")
def validate_notion():
    return notion_service.validate_schema()