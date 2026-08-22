from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas.request import PurchaseRequestIn, PurchaseRequestOut
from app.services import procurement_service

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
settings = get_settings()


@router.post("/purchase-request", response_model=PurchaseRequestOut)
def purchase_request_webhook(
    payload: PurchaseRequestIn,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None),
):
    """Real inbound trigger - e.g. from a Slack app, an internal HR tool,
    or a form service. Same handling path as the direct API, plus a
    shared-secret check since this is meant to be called by other systems."""
    if settings.webhook_secret and settings.webhook_secret != "change-me":
        if x_webhook_secret != settings.webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    return procurement_service.submit_purchase_request(db, payload)
