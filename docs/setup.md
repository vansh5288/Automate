# Setup & Testing Notes

## Quick start (mock mode, no external credentials)

This gets the full pipeline running locally with the mock AI provider and Notion/email in DEV_MODE — useful for developing and running the test suite without any API keys.

```bash
cp .env.example .env          # AI_PROVIDER already defaults to "mock"
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In another terminal:
```bash
curl -X POST http://localhost:8000/api/requests \
  -H "Content-Type: application/json" \
  -d '{"employee_name":"Rahul Sharma","employee_email":"rahul@example.com","department":"Engineering","request_text":"I need 5 keyboards for the engineering team."}'
```

## Switching to real AI / Notion / email for the demo

1. Set `AI_PROVIDER=openai` (or `anthropic`) and `AI_API_KEY` in `.env`.
2. Follow the Notion Setup steps in the main README, then set `NOTION_TOKEN` and the three database IDs.
3. Set `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `PROCUREMENT_EMAIL` (a real SMTP relay, e.g. Gmail with an app password, SendGrid, Mailgun).
4. Restart the backend. `notion_service.DEV_MODE` and `action_service.DEV_MODE` will both flip to `False` automatically once the relevant variables are present.

## Test suite

```bash
cd backend
pytest -v
```

What's covered (`tests/test_workflow.py`):

- **Validation** — blank fields, invalid email, too-short text, oversized input rejected by Pydantic rather than crashing downstream.
- **Mock AI provider** — known items extracted correctly, vague requests flagged low-confidence, high-value items flagged high-risk.
- **Decision engine** — each rule branch (amount over limit, low confidence, unusual category) independently triggers `approval_required`.
- **Idempotency** — same normalized inputs hash identically; different inputs don't collide.
- **End-to-end workflow** (real DB, mock AI, Notion in DEV_MODE) — auto-process path, approval-required path, ambiguous/needs-review path, duplicate submission returns the original request without creating a second row, Run Log rows exist for each step, self-approval is blocked, human approve/reject both resolve correctly.
- **Failure injection** — AI provider failure, Notion failure, and email failure are each simulated via `monkeypatch` and asserted to leave the request in a safe, visible state (`NEEDS_REVIEW` / `ACTION_FAILED`) rather than crashing or silently succeeding.

Note: these tests exercise the **mock** AI provider and Notion's **DEV_MODE** by design, so they run without any external credentials or network access. They validate the orchestration logic, not the live OpenAI/Notion/SMTP integrations themselves — run the manual `curl` / `seed_demo_data.py` flow against real credentials before the actual demo to confirm those.
