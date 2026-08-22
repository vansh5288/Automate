"""AI extraction service.

Provider is selected via AI_PROVIDER env var: openai | anthropic | mock.
The mock provider is a clearly-labeled, rule-based development fallback -
it is NOT used in place of real AI in the demo; it exists only so the app
can be developed/tested without an API key.
"""
import json
import logging
import re
from dataclasses import dataclass, asdict

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EXTRACTION_SYSTEM_PROMPT = """You are a procurement request parser for a corporate purchasing system.
Extract structured data from an employee's natural-language purchase request.

Respond with ONLY a JSON object (no markdown fences, no commentary) matching this schema:
{
  "item": string,
  "quantity": integer,
  "category": string,           // one of: IT Hardware, Office Supplies, Software, Furniture, Travel, Services, Other
  "department": string,
  "reason": string,
  "estimated_amount": number,   // your best estimate in INR
  "currency": "INR",
  "priority": string,           // Low, Medium, High
  "confidence": number,         // 0.0-1.0, how confident you are in this extraction
  "risk_level": string,         // Low, Medium, High
  "requires_approval": boolean
}

Guidance:
- High-value items (laptops, MacBooks, large quantities) => higher estimated_amount, Medium/High risk.
- Vague requests with no concrete item/quantity => low confidence (< 0.5) and risk_level "High".
- Routine small office items under typical budget => Low risk.
"""


@dataclass
class AIExtraction:
    item: str
    quantity: int
    category: str
    department: str
    reason: str
    estimated_amount: float
    currency: str
    priority: str
    confidence: float
    risk_level: str
    requires_approval: bool
    provider: str
    raw_error: str = ""

    def to_dict(self):
        return asdict(self)


class AIServiceError(Exception):
    pass


class BaseAIProvider:
    name = "base"

    def extract(self, request_text: str, department_hint: str) -> AIExtraction:
        raise NotImplementedError


class MockAIProvider(BaseAIProvider):
    """Deterministic, rule-based stand-in for a real LLM call.

    Clearly labeled as a development mock (see AIExtraction.provider == 'mock').
    Never presented as real AI output.
    """

    name = "mock"

    ITEM_PRICES = {
        "keyboard": 1200, "mouse": 800, "monitor": 9500, "laptop": 65000,
        "macbook": 140000, "chair": 7000, "desk": 12000, "headset": 2500,
        "webcam": 3500, "printer": 18000, "phone": 40000, "tablet": 35000,
        "license": 5000, "software": 15000,
    }

    def extract(self, request_text: str, department_hint: str) -> AIExtraction:
        text = request_text.lower()

        qty_match = re.search(r"\b(\d+)\b", text)
        quantity = int(qty_match.group(1)) if qty_match else 1

        found_item, unit_price = None, 0
        for key, price in self.ITEM_PRICES.items():
            if key in text:
                found_item, unit_price = key, price
                break

        if not found_item:
            # Vague / unrecognized request -> low confidence, needs human review
            return AIExtraction(
                item="Unspecified",
                quantity=quantity,
                category="Other",
                department=department_hint,
                reason=request_text[:200],
                estimated_amount=0,
                currency="INR",
                priority="Medium",
                confidence=0.35,
                risk_level="High",
                requires_approval=True,
                provider=self.name,
            )

        category_map = {
            "keyboard": "IT Hardware", "mouse": "IT Hardware", "monitor": "IT Hardware",
            "laptop": "IT Hardware", "macbook": "IT Hardware", "webcam": "IT Hardware",
            "phone": "IT Hardware", "tablet": "IT Hardware", "printer": "IT Hardware",
            "chair": "Furniture", "desk": "Furniture", "headset": "IT Hardware",
            "license": "Software", "software": "Software",
        }
        category = category_map.get(found_item, "Other")
        estimated_amount = unit_price * quantity
        high_value = found_item in ("laptop", "macbook", "phone", "tablet", "printer")
        risk_level = "High" if (high_value or estimated_amount > settings.auto_approval_limit) else "Low"
        priority = "High" if high_value else "Medium"

        return AIExtraction(
            item=found_item.capitalize(),
            quantity=quantity,
            category=category,
            department=department_hint,
            reason=request_text[:200],
            estimated_amount=float(estimated_amount),
            currency="INR",
            priority=priority,
            confidence=0.9 if found_item else 0.5,
            risk_level=risk_level,
            requires_approval=(risk_level == "High"),
            provider=self.name,
        )


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.ai_api_key)

    def extract(self, request_text: str, department_hint: str) -> AIExtraction:
        try:
            resp = self.client.chat.completions.create(
                model=settings.ai_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Department: {department_hint}\nRequest: {request_text}"},
                ],
                temperature=0,
            )
            data = json.loads(resp.choices[0].message.content)
            return AIExtraction(provider=self.name, **data)
        except Exception as exc:  # noqa: BLE001
            logger.exception("OpenAI extraction failed")
            raise AIServiceError(str(exc)) from exc


class AnthropicProvider(BaseAIProvider):
    name = "anthropic"

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=settings.ai_api_key)

    def extract(self, request_text: str, department_hint: str) -> AIExtraction:
        try:
            resp = self.client.messages.create(
                model=settings.ai_model or "claude-sonnet-4-6",
                max_tokens=500,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"Department: {department_hint}\nRequest: {request_text}"}],
            )
            text = resp.content[0].text.strip()
            text = re.sub(r"^```json|```$", "", text).strip()
            data = json.loads(text)
            return AIExtraction(provider=self.name, **data)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Anthropic extraction failed")
            raise AIServiceError(str(exc)) from exc


def get_ai_provider() -> BaseAIProvider:
    provider = settings.ai_provider.lower()
    if provider == "openai" and settings.ai_api_key:
        return OpenAIProvider()
    if provider == "anthropic" and settings.ai_api_key:
        return AnthropicProvider()
    if provider in ("openai", "anthropic") and not settings.ai_api_key:
        logger.warning("AI_PROVIDER=%s set but AI_API_KEY missing; falling back to mock provider", provider)
    return MockAIProvider()


def extract_purchase_details(request_text: str, department_hint: str) -> AIExtraction:
    provider = get_ai_provider()
    try:
        return provider.extract(request_text, department_hint)
    except AIServiceError:
        # Surface failure to caller instead of pretending it worked
        raise
