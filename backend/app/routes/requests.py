from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.request import PurchaseRequest, RequestStatus
from app.models.run_log import RunLog
from app.schemas.request import PurchaseRequestIn, PurchaseRequestOut, RequestDetail
from app.services import procurement_service

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.post("", response_model=PurchaseRequestOut)
def create_request(payload: PurchaseRequestIn, db: Session = Depends(get_db)):
    return procurement_service.submit_purchase_request(db, payload)


@router.get("")
def list_requests(db: Session = Depends(get_db)):
    reqs = db.query(PurchaseRequest).order_by(PurchaseRequest.created_at.desc()).all()
    return [
        {
            "request_id": r.id,
            "employee_name": r.employee_name,
            "department": r.department,
            "item": r.item,
            "quantity": r.quantity,
            "estimated_amount": r.estimated_amount,
            "status": r.status.value,
            "risk_level": r.risk_level,
            "approval_required": bool(r.approval_required),
            "created_at": r.created_at.isoformat(),
        }
        for r in reqs
    ]


@router.get("/{request_id}", response_model=RequestDetail)
def get_request(request_id: str, db: Session = Depends(get_db)):
    r = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    return RequestDetail(
        request_id=r.id,
        employee_name=r.employee_name,
        employee_email=r.employee_email,
        department=r.department,
        request_text=r.request_text,
        item=r.item,
        category=r.category,
        quantity=r.quantity,
        estimated_amount=r.estimated_amount,
        currency=r.currency,
        priority=r.priority,
        risk_level=r.risk_level,
        confidence=r.confidence,
        ai_reasoning=r.ai_reasoning,
        approval_required=bool(r.approval_required),
        status=r.status.value,
        approver=r.approver,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat(),
    )


@router.get("/{request_id}/runs")
def get_run_history(request_id: str, db: Session = Depends(get_db)):
    r = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    logs = (
        db.query(RunLog)
        .filter(RunLog.request_id == request_id)
        .order_by(RunLog.timestamp.asc())
        .all()
    )
    return [
        {
            "run_id": l.run_id,
            "event": l.event,
            "status": l.status,
            "action": l.action,
            "actor": l.actor,
            "reason": l.reason,
            "error": l.error,
            "external_action_id": l.external_action_id,
            "timestamp": l.timestamp.isoformat(),
        }
        for l in logs
    ]


@router.post("/{request_id}/retry", response_model=PurchaseRequestOut)
def retry_request(request_id: str, db: Session = Depends(get_db)):
    r = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    if r.status not in (RequestStatus.FAILED, RequestStatus.NEEDS_REVIEW, RequestStatus.ACTION_FAILED):
        raise HTTPException(status_code=400, detail=f"Request in status {r.status.value} is not retryable")
    return procurement_service._process_request(db, r)  # noqa: SLF001 - intentional reuse
