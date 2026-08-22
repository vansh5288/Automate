# Hackathon Compliance — Notion Track

Honest mapping of Automate India's Notion Track requirements to what is
actually implemented in this repo. Nothing below is claimed unless the
corresponding code exists and runs.

| Requirement | Implementation | Where |
|---|---|---|
| Real automated job | Corporate purchase-request intake, classification, risk decisioning, and procurement notification | `backend/app/services/procurement_service.py` |
| Trigger | HTTP webhook (`/api/webhooks/purchase-request`) plus the direct API endpoint; both run the same pipeline | `backend/app/routes/webhooks.py` |
| Our code is the engine | FastAPI service owns validation, AI extraction, the deterministic decision engine, Notion sync, and the external action — not a script run by hand | `backend/app/main.py`, `backend/app/services/*` |
| Human approval/override inside Notion | High-risk/ambiguous requests get a row in the Notion Approval Queue; a background poller reads the human's Approved/Rejected/Override decision and resumes the workflow | `backend/app/services/notion_service.py`, `backend/app/workers/notion_poller.py` |
| Real external action | A procurement notification email is sent (real SMTP when configured; a labeled dev-mode fallback otherwise — never silently claimed as sent) | `backend/app/services/action_service.py` |
| Run Log written by our code | Every workflow step (`REQUEST_RECEIVED`, `AI_CLASSIFIED`, `RISK_DECISION`, `NOTION_RECORD_CREATED`, `EXTERNAL_ACTION`, `HUMAN_DECISION`, etc.) writes a timestamped row to SQLite and mirrors it into the Notion Run Log DB at the moment it happens — never pre-generated | `backend/app/services/run_log_service.py` |
| Bad input / duplicate / failure handling | Pydantic validation (length limits, required fields), SHA-256 request-hash idempotency, retry-with-backoff around Notion, and explicit `NEEDS_REVIEW` / `FAILED` / `ACTION_FAILED` states instead of crashes | `backend/app/schemas/request.py`, `backend/app/utils/idempotency.py`, `backend/app/services/notion_service.py` |
| Notion as human-readable ops workspace | Three databases (Purchase Requests, Approval Queue, Run Log) with typed Select/Number/Checkbox properties, not a dump of raw JSON text | `scripts/setup_notion.py` |
| AI adds genuine value | Natural-language extraction of item/quantity/category/amount/risk feeds a deterministic policy engine; AI never has unilateral authority to approve spend | `backend/app/services/ai_service.py`, `backend/app/services/risk_service.py` |

## Explicit non-claims

- The **mock AI provider** (`AI_PROVIDER=mock`) is a rule-based development fallback used when no `AI_API_KEY` is configured. It is clearly labeled (`provider: "mock"` on every extraction) and is not presented as real AI in a demo — set `AI_PROVIDER=openai` or `anthropic` with a real key for the actual demo run.
- **Notion DEV_MODE**: if `NOTION_TOKEN` or the database IDs are missing, `notion_service.py` logs what it *would* send instead of faking success. The Approval Queue poller (`notion_poller.py`) is a no-op in this mode since there is nothing to poll.
- **Email DEV_MODE**: if SMTP credentials are missing, `action_service.py` logs the exact email that would be sent and returns a `dev-email-*` action ID — it never marks a request `COMPLETED` while claiming a real email went out under false pretenses; the log line makes the mode explicit.
- These dev-mode fallbacks exist so the pipeline can be developed and unit-tested without live credentials. **For the actual hackathon demo, real `NOTION_TOKEN`, `AI_API_KEY`, and SMTP credentials should be configured** so all three verifications above are live.
