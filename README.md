# ProcureFlow

AI-powered corporate purchase approval agent — built for the **Automate India Hackathon, Notion Track**.

## Problem

Corporate purchase requests are slow and inconsistent: employees email or Slack a manager, someone eventually reads it, checks a budget in their head, and replies. Routine, low-value purchases wait in the same queue as ones that genuinely need scrutiny, and there's no audit trail of who decided what, when.

## Solution

Employees submit a request in plain language. ProcureFlow uses AI to extract what's actually being asked for (item, quantity, category, estimated cost), runs it through a **deterministic, configurable policy engine** (not the AI) to decide whether it's routine or risky, and:

- **Auto-processes** routine, low-value, high-confidence requests — sending a real procurement notification email.
- **Routes to a human** in Notion for anything expensive, ambiguous, low-confidence, or unusual — where a manager approves, rejects, or overrides.

Every step writes a timestamped Run Log entry, in the app's own database and mirrored into Notion, so the whole thing is auditable.

## Architecture

```mermaid
flowchart LR
    E[Employee] -->|POST /api/requests or webhook| API[FastAPI Backend]
    API --> AI[AI Extraction]
    AI --> DE[Decision Engine]
    DE -->|low risk| ACT[External Action: Email]
    DE -->|high risk / low confidence| NQ[Notion Approval Queue]
    NQ -->|poller detects decision| API
    NQ -->|approved/override| ACT
    API --> RL[(Run Log: SQLite + Notion)]
    API --> DB[(SQLite: requests, approvals)]
    NQ -.human approves/rejects.-> Manager((Manager))
```

See `docs/architecture.md` for the full request lifecycle diagram.

## Features

- Natural-language purchase request intake (API + webhook)
- Configurable AI provider: OpenAI, Anthropic, or a labeled rule-based mock for offline development
- Deterministic policy engine (amount threshold, confidence threshold, category checks) — the AI never has unilateral approval authority
- Notion as the human-readable control plane: Purchase Requests DB, Approval Queue, Run Log
- Background poller that detects human decisions in Notion and resumes the workflow — no manual script required during a demo
- Real external action: procurement notification email (SMTP), with a transparent dev-mode fallback
- Idempotency via request hashing — duplicate submissions never double-process
- Retry-with-backoff around Notion, explicit `FAILED` / `NEEDS_REVIEW` / `ACTION_FAILED` states instead of crashes
- React dashboard for visibility (not the system of record — Notion and the backend are)

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **AI:** OpenAI / Anthropic (configurable), with a rule-based mock fallback
- **Control plane:** Notion API (`notion-client`)
- **Frontend:** React + Vite
- **External action:** SMTP email

## Notion Setup

ProcureFlow creates a **ProcureFlow Control Center** page in your Notion workspace with three databases:

| Database | Purpose |
|---|---|
| **Purchase Requests** | Master record of every request |
| **Approval Queue** | Human approval control panel for high-risk purchases |
| **Run Log** | Audit trail of every workflow step |

### Step-by-step setup

1. Create an internal integration at [notion.so/my-integrations](https://www.notion.so/my-integrations) and copy the **Internal Integration Secret**.
2. In Notion, create a page (e.g. "ProcureFlow Control Center") and use **⋯ → Add connections** to share it with your integration.
3. Copy the page ID from the URL (the 32-character hex string after the workspace name).
4. Add to `.env`:
   ```
   NOTION_TOKEN=secret_...
   NOTION_PARENT_PAGE_ID=your_page_id
   DEMO_MODE=false
   ```
5. Run the setup script (creates databases with the correct schema):
   ```powershell
   cd backend
   .\venv\Scripts\python.exe ..\scripts\setup_notion.py --parent-page-id <page_id>
   ```
6. Copy the three printed database IDs into `.env`:
   ```
   NOTION_REQUESTS_DATABASE_ID=...
   NOTION_APPROVALS_DATABASE_ID=...
   NOTION_RUN_LOG_DATABASE_ID=...
   ```
7. Restart the backend.
8. Open **Integrations** in the frontend → **Test Connection / Validate Schema** — you should see **🟢 Notion Connected**.
9. Submit a high-risk request (e.g. "3 MacBook Pro laptops for engineering").
10. Confirm it appears in the **Approval Queue** database in Notion.
11. Click **Open in Notion** on the request detail page — it must open the exact approval row.
12. Change **Status** from `Pending` to `Approved` or `Rejected` in Notion.
13. Wait ~15 seconds (background poller) or click **Sync Now** — ProcureFlow processes the decision and updates the Run Log.

If setup fails with "object not found" or "forbidden", re-share the parent page **and all three databases** with your integration.

### Without Notion configured

The app runs in **🟡 Demo / Local Mode**:

- No fake Notion URLs are shown
- High-risk requests show **Approve (Demo)** / **Reject (Demo)** buttons on the request detail page
- Run logs are stored locally in SQLite only

### DEMO_MODE

`DEMO_MODE=true` in `.env` simulates **external procurement actions** (email) without requiring SMTP. It does **not** disable Notion when `NOTION_TOKEN` and database IDs are configured.

| Component | DEMO_MODE=false | DEMO_MODE=true |
|---|---|---|
| Notion approvals | Real (if configured) | Real (if configured) |
| Procurement email | Real (if SMTP configured) | Simulated (`dev-email-*` ID logged) |
| "Open in Notion" link | Shown only when real URL exists | Same — never faked |

Without Notion credentials, the system is always in local demo mode regardless of `DEMO_MODE`.

## Environment Variables

See `.env.example` at the repo root for the full list (Notion, AI provider, SMTP, policy thresholds, webhook secret). Copy it to `.env` and fill in real values before the demo:

```bash
cp .env.example .env
```

## Local Installation

```bash
# Backend
cd backend
py -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

## Running Backend

PowerShell (Windows):

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

macOS/Linux (after activating the virtual environment):

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000/health` and `http://localhost:8000/docs` (auto-generated API docs).

## Running Frontend

```bash
cd frontend
npm run dev
```
Visit `http://localhost:5173`. Set `VITE_API_BASE_URL` if the backend isn't on `localhost:8000`, and `VITE_NOTION_WORKSPACE_URL` to point the "Open Notion Workspace" button at your real workspace.

## Running Tests

```bash
cd backend
pytest -v
```

Covers request validation, the mock AI provider, the decision engine's rule branches, idempotency hashing, and full end-to-end workflow runs (auto-process, approval-required, ambiguous/needs-review, duplicate detection, self-approval blocking, human approve/reject, and AI/Notion/action failure handling). See `docs/setup.md` for what each test group verifies.

## Demo Scenarios

With the backend running:
```bash
python scripts/seed_demo_data.py --base-url http://localhost:8000
```

1. **Automatic** — "5 keyboards for engineering" → low risk → auto-processed → email sent → Run Log.
2. **Human approval** — "3 MacBook Pro laptops for data science" → high risk → Notion Approval Queue → approve in Notion → poller detects it → email sent → Run Log.
3. **Bad input** — "I need something urgently" → low confidence → Needs Review, no external action → Run Log.

## API Documentation

Interactive docs at `/docs` (Swagger) once the backend is running. Core endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/api/requests` | Submit a purchase request |
| GET | `/api/requests` | List all requests |
| GET | `/api/requests/{id}` | Full detail for one request |
| GET | `/api/requests/{id}/runs` | Run Log history for one request |
| POST | `/api/requests/{id}/decide` | Demo-only local approve/reject when Notion is not connected |
| POST | `/api/requests/{id}/retry` | Re-run processing after a failure |
| POST | `/api/requests/{id}/sync` | Poll Notion and synchronize one request |
| POST | `/api/webhooks/purchase-request` | Webhook trigger (same pipeline as above) |
| GET | `/api/integrations/status` | Safe AI/Notion/poller integration diagnostics |
| POST | `/api/integrations/notion/validate` | Test Notion access and required properties |
| GET | `/api/notion/status` | Real Notion authentication and database status |
| POST | `/api/notion/setup` | Discover or create the ProcureFlow Notion hierarchy |
| POST | `/api/notion/sync` | Poll all pending Notion approvals immediately |

## Failure Handling

See `docs/hackathon-compliance.md` for the full mapping. Summary: AI failures → `NEEDS_REVIEW`; Notion failures → retried with exponential backoff, then logged as a failure without crashing the request; external action (email) failures → `ACTION_FAILED`, never silently marked complete; malformed/duplicate input never creates a second action.

## Security

- All secrets via environment variables; `.env` is gitignored
- Optional shared-secret header (`X-Webhook-Secret`) on the webhook endpoint
- CORS restricted outside development
- Input validated and length-capped with Pydantic
- No API keys or tokens ever sent to the frontend

## Deployment

See `DEPLOYMENT.md`.

## Future Improvements

- Multi-level approval chains for very large purchases
- Slack notifications alongside email
- Budget-aware risk scoring per department
- Webhook signature verification (HMAC) instead of a shared secret
