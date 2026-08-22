import logging

from sqlalchemy.orm import Session

from app.models.request import PurchaseRequest, RequestStatus
from app.models.approval import Approval
from app.schemas.request import PurchaseRequestIn, PurchaseRequestOut
from app.services import ai_service, risk_service, notion_service, action_service, run_log_service
from app.services.ai_service import AIServiceError
from app.services.action_service import ActionError
from app.utils.idempotency import compute_request_hash, generate_request_id

logger = logging.getLogger(__name__)


def _next_sequence(db: Session) -> int:
    return db.query(PurchaseRequest).count() + 1


def find_duplicate(db: Session, request_hash: str) -> PurchaseRequest | None:
    return db.query(PurchaseRequest).filter(PurchaseRequest.request_hash == request_hash).first()


def submit_purchase_request(db: Session, payload: PurchaseRequestIn) -> PurchaseRequestOut:
    request_hash = compute_request_hash(payload.employee_email, payload.department, payload.request_text)

    existing = find_duplicate(db, request_hash)
    if existing:
        logger.info("Duplicate request detected, returning existing %s", existing.id)
        return PurchaseRequestOut(
            request_id=existing.id,
            status=existing.status.value,
            approval_required=bool(existing.approval_required),
            message="Duplicate request detected - returning the original request's status.",
        )

    req = PurchaseRequest(
        id=generate_request_id(_next_sequence(db)),
        request_hash=request_hash,
        employee_name=payload.employee_name,
        employee_email=payload.employee_email,
        department=payload.department,
        request_text=payload.request_text,
        status=RequestStatus.RECEIVED,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    run_log_service.write_run_log(db, request_id=req.id, event="REQUEST_RECEIVED", status="SUCCESS")

    return _process_request(db, req)


def _process_request(db: Session, req: PurchaseRequest) -> PurchaseRequestOut:
    req.status = RequestStatus.PROCESSING
    db.commit()

    # --- AI extraction ---
    try:
        extraction = ai_service.extract_purchase_details(req.request_text, req.department)
        run_log_service.write_run_log(
            db, request_id=req.id, event="AI_CLASSIFIED", status="SUCCESS",
            reason=f"provider={extraction.provider}, confidence={extraction.confidence}",
        )
    except AIServiceError as exc:
        req.status = RequestStatus.NEEDS_REVIEW
        db.commit()
        run_log_service.write_run_log(
            db, request_id=req.id, event="AI_CLASSIFIED", status="FAILURE", error=str(exc),
        )
        _create_notion_records(db, req, ai_reasoning="AI service unavailable - routed to manual review")
        return _out(req, "AI service unavailable; request routed to human review.")

    req.item = extraction.item
    req.category = extraction.category
    req.quantity = extraction.quantity
    req.estimated_amount = extraction.estimated_amount
    req.currency = extraction.currency
    req.priority = extraction.priority
    req.risk_level = extraction.risk_level
    req.confidence = extraction.confidence
    req.ai_reasoning = extraction.reason
    db.commit()

    # --- Decision engine ---
    decision = risk_service.decide(extraction)
    req.approval_required = int(decision.approval_required)
    run_log_service.write_run_log(
        db, request_id=req.id, event="RISK_DECISION", status="SUCCESS", reason=decision.reason,
    )

    if extraction.confidence < 0.5 and extraction.item in ("", "Unspecified"):
        req.status = RequestStatus.NEEDS_REVIEW
        db.commit()
        _create_notion_records(db, req, ai_reasoning=decision.reason, force_approval_item=True)
        run_log_service.write_run_log(db, request_id=req.id, event="ROUTED_NEEDS_REVIEW", status="SUCCESS")
        return _out(req, "Request too ambiguous for automatic processing - sent for human review.")

    if decision.auto_process:
        return _auto_process(db, req)

    req.status = RequestStatus.PENDING_APPROVAL
    db.commit()
    _create_notion_records(db, req, ai_reasoning=decision.reason, force_approval_item=True)
    run_log_service.write_run_log(db, request_id=req.id, event="ROUTED_TO_APPROVAL", status="SUCCESS", reason=decision.reason)
    return _out(req, "Purchase requires human approval - sent to Notion Approval Queue.")


def _create_notion_records(db: Session, req: PurchaseRequest, ai_reasoning: str = "", force_approval_item: bool = False):
    try:
        page_id = notion_service.create_purchase_request_page(req)
        req.notion_page_id = page_id
        db.commit()
        run_log_service.write_run_log(db, request_id=req.id, event="NOTION_RECORD_CREATED", status="SUCCESS")
    except Exception as exc:  # noqa: BLE001
        run_log_service.write_run_log(db, request_id=req.id, event="NOTION_RECORD_CREATED", status="FAILURE", error=str(exc))

    if force_approval_item or req.approval_required:
        try:
            approval_page_id = notion_service.create_approval_item(req)
            req.notion_approval_page_id = approval_page_id
            db.commit()
            approval = Approval(request_id=req.id, status="PENDING")
            db.add(approval)
            db.commit()
            run_log_service.write_run_log(db, request_id=req.id, event="APPROVAL_ITEM_CREATED", status="SUCCESS")
        except Exception as exc:  # noqa: BLE001
            run_log_service.write_run_log(db, request_id=req.id, event="APPROVAL_ITEM_CREATED", status="FAILURE", error=str(exc))


def _auto_process(db: Session, req: PurchaseRequest) -> PurchaseRequestOut:
    req.status = RequestStatus.AUTO_PROCESSED
    db.commit()
    _create_notion_records(db, req)

    try:
        action_id = action_service.send_procurement_notification(req, approved_by="Auto-Processing (policy rules)")
        req.external_action_id = action_id
        req.status = RequestStatus.COMPLETED
        db.commit()
        run_log_service.write_run_log(
            db, request_id=req.id, event="EXTERNAL_ACTION", status="SUCCESS",
            action="send_procurement_email", external_action_id=action_id,
        )
        if req.notion_page_id:
            notion_service.update_purchase_request_status(req.notion_page_id, "Completed")
        return _out(req, "Routine purchase auto-processed and procurement notified.")
    except ActionError as exc:
        req.status = RequestStatus.ACTION_FAILED
        db.commit()
        run_log_service.write_run_log(
            db, request_id=req.id, event="EXTERNAL_ACTION", status="FAILURE",
            action="send_procurement_email", error=str(exc),
        )
        return _out(req, "Auto-processing decision succeeded but the external action failed.")


def apply_human_decision(db: Session, req: PurchaseRequest, decision: str, approver: str, reason: str = "") -> PurchaseRequestOut:
    """decision: APPROVED | REJECTED | OVERRIDDEN.
    Called by the Notion polling worker (or a manual retry) once a human
    has acted in the Approval Queue."""
    approval = (
        db.query(Approval)
        .filter(Approval.request_id == req.id, Approval.status == "PENDING")
        .first()
    )

    if approver.strip().lower() == req.employee_email.strip().lower():
        run_log_service.write_run_log(
            db, request_id=req.id, event="SELF_APPROVAL_BLOCKED", status="FAILURE",
            reason="Requestor cannot approve their own high-risk request",
        )
        return _out(req, "Self-approval blocked: the requesting employee cannot approve their own request.")

    from datetime import datetime, timezone
    if approval:
        approval.status = decision
        approval.approver = approver
        approval.decision = decision
        approval.reason = reason
        approval.decided_at = datetime.now(timezone.utc)
        db.commit()

    req.approver = approver

    if decision in ("APPROVED", "OVERRIDDEN"):
        req.status = RequestStatus.APPROVED
        db.commit()
        run_log_service.write_run_log(
            db, request_id=req.id, event="HUMAN_DECISION", status="SUCCESS",
            actor=approver, action=decision, reason=reason,
        )
        return _auto_process(db, req)

    req.status = RequestStatus.REJECTED
    db.commit()
    run_log_service.write_run_log(
        db, request_id=req.id, event="HUMAN_DECISION", status="SUCCESS",
        actor=approver, action="REJECTED", reason=reason,
    )
    if req.notion_page_id:
        try:
            notion_service.update_purchase_request_status(req.notion_page_id, "Rejected", approver)
        except Exception as exc:  # noqa: BLE001
            run_log_service.write_run_log(db, request_id=req.id, event="NOTION_STATUS_SYNC", status="FAILURE", error=str(exc))
    return _out(req, "Request rejected by human approver.")


def _out(req: PurchaseRequest, message: str) -> PurchaseRequestOut:
    return PurchaseRequestOut(
        request_id=req.id,
        status=req.status.value,
        approval_required=bool(req.approval_required),
        message=message,
    )
