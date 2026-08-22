import pytest
from pydantic import ValidationError

from app.schemas.request import PurchaseRequestIn
from app.services import ai_service, risk_service, procurement_service
from app.services.ai_service import MockAIProvider, AIExtraction
from app.models.request import RequestStatus
from app.utils.idempotency import compute_request_hash, generate_request_id


# ---------- Validation ----------

def test_valid_payload_parses():
    p = PurchaseRequestIn(
        employee_name="Rahul Sharma", employee_email="rahul@example.com",
        department="Engineering", request_text="I need 5 keyboards for the team.",
    )
    assert p.employee_name == "Rahul Sharma"


def test_blank_name_rejected():
    with pytest.raises(ValidationError):
        PurchaseRequestIn(
            employee_name="   ", employee_email="a@example.com",
            department="Eng", request_text="Need pens",
        )


def test_bad_email_rejected():
    with pytest.raises(ValidationError):
        PurchaseRequestIn(
            employee_name="A", employee_email="not-an-email",
            department="Eng", request_text="Need pens",
        )


def test_too_short_request_text_rejected():
    with pytest.raises(ValidationError):
        PurchaseRequestIn(
            employee_name="A", employee_email="a@example.com",
            department="Eng", request_text="hi",
        )


def test_extremely_long_input_does_not_crash():
    long_text = "keyboard " * 2000
    with pytest.raises(ValidationError):
        PurchaseRequestIn(
            employee_name="A", employee_email="a@example.com",
            department="Eng", request_text=long_text,
        )


# ---------- AI mock provider ----------

def test_mock_provider_extracts_known_item():
    provider = MockAIProvider()
    result = provider.extract("I need 5 keyboards for the team", "Engineering")
    assert result.item == "Keyboard"
    assert result.quantity == 5
    assert result.provider == "mock"


def test_mock_provider_low_confidence_on_vague_request():
    provider = MockAIProvider()
    result = provider.extract("I need something urgently for the team.", "Engineering")
    assert result.confidence < 0.5
    assert result.item == "Unspecified"


def test_mock_provider_flags_high_value_item():
    provider = MockAIProvider()
    result = provider.extract("We need 3 MacBook Pro laptops", "Data Science")
    assert result.risk_level == "High"
    assert result.requires_approval is True


# ---------- Decision engine ----------

def _extraction(**overrides):
    base = dict(
        item="Keyboard", quantity=5, category="IT Hardware", department="Eng",
        reason="", estimated_amount=6000, currency="INR", priority="Low",
        confidence=0.9, risk_level="Low", requires_approval=False, provider="mock",
    )
    base.update(overrides)
    return AIExtraction(**base)


def test_low_risk_auto_processes():
    decision = risk_service.decide(_extraction())
    assert decision.auto_process is True
    assert decision.approval_required is False


def test_high_amount_requires_approval():
    decision = risk_service.decide(_extraction(estimated_amount=200000))
    assert decision.approval_required is True


def test_low_confidence_requires_approval():
    decision = risk_service.decide(_extraction(confidence=0.4))
    assert decision.approval_required is True


def test_unusual_category_requires_approval():
    decision = risk_service.decide(_extraction(category="Exotic Animals"))
    assert decision.approval_required is True


# ---------- Idempotency ----------

def test_same_inputs_produce_same_hash():
    h1 = compute_request_hash("a@example.com", "Eng", "Need 5 keyboards")
    h2 = compute_request_hash("A@Example.com", " Eng ", "need 5 keyboards")
    assert h1 == h2


def test_different_inputs_produce_different_hash():
    h1 = compute_request_hash("a@example.com", "Eng", "Need 5 keyboards")
    h2 = compute_request_hash("a@example.com", "Eng", "Need 6 keyboards")
    assert h1 != h2


def test_generate_request_id_format():
    rid = generate_request_id(7)
    assert rid.startswith("REQ-")
    assert rid.endswith("-0007") or rid.split("-")[-1] == "0007"


# ---------- End-to-end workflow (DB + mock AI, Notion in DEV_MODE) ----------

def test_full_workflow_auto_process(db_session, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    payload = PurchaseRequestIn(
        employee_name="Priya", employee_email="priya@example.com",
        department="Engineering", request_text="I need 5 keyboards for the engineering team.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)
    assert result.status in ("COMPLETED", "ACTION_FAILED")
    assert result.approval_required is False


def test_full_workflow_requires_approval(db_session):
    payload = PurchaseRequestIn(
        employee_name="Ananya", employee_email="ananya@example.com",
        department="Data Science", request_text="We need 3 MacBook Pro laptops for the new data science team.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)
    assert result.status == "PENDING_APPROVAL"
    assert result.approval_required is True


def test_vague_request_routed_to_review(db_session):
    payload = PurchaseRequestIn(
        employee_name="Karan", employee_email="karan@example.com",
        department="Ops", request_text="I need something urgently for the team.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)
    assert result.status == "NEEDS_REVIEW"


def test_duplicate_request_does_not_create_second_record(db_session):
    payload = PurchaseRequestIn(
        employee_name="Priya", employee_email="priya2@example.com",
        department="Engineering", request_text="I need 5 keyboards for the engineering team.",
    )
    first = procurement_service.submit_purchase_request(db_session, payload)
    second = procurement_service.submit_purchase_request(db_session, payload)
    assert first.request_id == second.request_id

    from app.models.request import PurchaseRequest
    count = db_session.query(PurchaseRequest).filter(
        PurchaseRequest.employee_email == "priya2@example.com"
    ).count()
    assert count == 1


def test_run_log_written_for_each_step(db_session):
    payload = PurchaseRequestIn(
        employee_name="Dev", employee_email="dev@example.com",
        department="Engineering", request_text="I need 2 mouse for interns.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)

    from app.models.run_log import RunLog
    logs = db_session.query(RunLog).filter(RunLog.request_id == result.request_id).all()
    events = {l.event for l in logs}
    assert "REQUEST_RECEIVED" in events
    assert "AI_CLASSIFIED" in events
    assert "RISK_DECISION" in events


def test_self_approval_is_blocked(db_session):
    payload = PurchaseRequestIn(
        employee_name="Ananya", employee_email="ananya2@example.com",
        department="Data Science", request_text="We need 3 MacBook Pro laptops for the team.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)
    from app.models.request import PurchaseRequest
    req = db_session.query(PurchaseRequest).filter(PurchaseRequest.id == result.request_id).first()

    out = procurement_service.apply_human_decision(db_session, req, "APPROVED", approver="ananya2@example.com")
    assert "Self-approval blocked" in out.message
    assert req.status == RequestStatus.PENDING_APPROVAL


def test_human_approval_completes_workflow(db_session):
    payload = PurchaseRequestIn(
        employee_name="Ananya", employee_email="ananya3@example.com",
        department="Data Science", request_text="We need 3 MacBook Pro laptops for the team.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)
    from app.models.request import PurchaseRequest
    req = db_session.query(PurchaseRequest).filter(PurchaseRequest.id == result.request_id).first()

    out = procurement_service.apply_human_decision(db_session, req, "APPROVED", approver="manager@example.com")
    assert out.status in ("COMPLETED", "ACTION_FAILED")


def test_human_rejection_stops_workflow(db_session):
    payload = PurchaseRequestIn(
        employee_name="Ananya", employee_email="ananya4@example.com",
        department="Data Science", request_text="We need 3 MacBook Pro laptops for the team.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)
    from app.models.request import PurchaseRequest
    req = db_session.query(PurchaseRequest).filter(PurchaseRequest.id == result.request_id).first()

    out = procurement_service.apply_human_decision(db_session, req, "REJECTED", approver="manager@example.com")
    assert out.status == "REJECTED"


def test_ai_failure_routes_to_needs_review(db_session, monkeypatch):
    def boom(*args, **kwargs):
        raise ai_service.AIServiceError("provider down")

    monkeypatch.setattr(ai_service, "extract_purchase_details", boom)
    payload = PurchaseRequestIn(
        employee_name="Dev", employee_email="dev2@example.com",
        department="Engineering", request_text="Need 5 keyboards please.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)
    assert result.status == "NEEDS_REVIEW"


def test_notion_failure_does_not_crash_workflow(db_session, monkeypatch):
    from app.services import notion_service

    def boom(*args, **kwargs):
        raise notion_service.NotionServiceError("notion down")

    monkeypatch.setattr(notion_service, "create_purchase_request_page", boom)
    payload = PurchaseRequestIn(
        employee_name="Dev", employee_email="dev3@example.com",
        department="Engineering", request_text="Need 5 keyboards please.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)
    # workflow still completes / reaches a terminal-ish state despite Notion failure
    assert result.status in ("COMPLETED", "ACTION_FAILED", "NEEDS_REVIEW", "PENDING_APPROVAL")


def test_external_action_failure_marks_action_failed(db_session, monkeypatch):
    from app.services import action_service

    def boom(*args, **kwargs):
        raise action_service.ActionError("smtp down")

    monkeypatch.setattr(action_service, "send_procurement_notification", boom)
    payload = PurchaseRequestIn(
        employee_name="Dev", employee_email="dev4@example.com",
        department="Engineering", request_text="Need 5 keyboards please.",
    )
    result = procurement_service.submit_purchase_request(db_session, payload)
    assert result.status == "ACTION_FAILED"
