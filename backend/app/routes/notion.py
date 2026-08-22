from fastapi import APIRouter, HTTPException

from app.services import notion_service

router = APIRouter(prefix="/api/notion", tags=["notion"])


@router.get("/status")
def notion_status():
    return notion_service.integration_status()


@router.post("/validate")
def validate_notion():
    return notion_service.validate_schema()


@router.post("/setup")
def setup_notion():
    parent_page_id = notion_service.settings.notion_parent_page_id
    if not parent_page_id:
        raise HTTPException(status_code=400, detail="Set NOTION_PARENT_PAGE_ID before running Notion setup.")
    try:
        return notion_service.setup_procureflow(parent_page_id)
    except notion_service.NotionServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync")
def sync_notion():
    from app.workers.notion_poller import poll_once
    return {"synced": poll_once()}