"""Deterministic decision engine.

The AI only extracts/estimates. Whether a request is auto-processed or
sent to a human is decided here by configurable rules - not by the AI.
"""
from dataclasses import dataclass

from app.config import get_settings
from app.services.ai_service import AIExtraction

settings = get_settings()

STANDARD_CATEGORIES = {"IT Hardware", "Office Supplies", "Software", "Furniture"}


@dataclass
class Decision:
    approval_required: bool
    auto_process: bool
    reason: str


def decide(extraction: AIExtraction) -> Decision:
    reasons = []

    if extraction.item in ("", "Unspecified"):
        reasons.append("missing/unclear item")
    if extraction.confidence < settings.min_ai_confidence:
        reasons.append(f"low AI confidence ({extraction.confidence:.2f} < {settings.min_ai_confidence})")
    if extraction.estimated_amount > settings.auto_approval_limit:
        reasons.append(f"amount ₹{extraction.estimated_amount:,.0f} exceeds auto-approval limit ₹{settings.auto_approval_limit:,.0f}")
    if extraction.category not in STANDARD_CATEGORIES:
        reasons.append(f"unusual category '{extraction.category}'")
    if extraction.risk_level == "High":
        reasons.append("AI flagged risk_level=High")

    if reasons:
        return Decision(approval_required=True, auto_process=False, reason="; ".join(reasons))

    return Decision(
        approval_required=False,
        auto_process=True,
        reason="Routine purchase within policy limits and confidence threshold",
    )
