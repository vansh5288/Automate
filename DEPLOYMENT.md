# Deployment

ProcureFlow is two small services: a FastAPI backend and a static-buildable React frontend. Neither needs expensive infrastructure.

## Backend (Render / Railway / Fly.io — any free-tier Python host)

Example for **Render**:
1. New Web Service → point at this repo, root directory `backend`.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all variables from `.env.example` in the dashboard's environment settings (real values, never committed).
5. Because SQLite is a file, use Render's persistent disk (or switch `DATABASE_URL` to a managed Postgres instance if you need durability across redeploys — the SQLAlchemy layer doesn't care which).

## Frontend (Vercel / Netlify)

1. Root directory `frontend`.
2. Build command: `npm run build`, output directory `dist`.
3. Environment variable `VITE_API_BASE_URL` → your deployed backend URL.
4. Optional `VITE_NOTION_WORKSPACE_URL` → your Notion workspace link for the "Open Notion Workspace" button.

## Docker Compose (local or a single VM)

```bash
cp .env.example .env   # fill in real values
docker compose up --build
```
Backend on `:8000`, frontend on `:5173`.

## Post-deploy checklist

- [ ] `.env` values are real, not placeholders (`NOTION_TOKEN`, `AI_API_KEY`, SMTP creds)
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `python scripts/seed_demo_data.py --base-url <deployed-url>` runs the three demo scenarios successfully
- [ ] The Notion Approval Queue shows a pending row for the MacBook demo scenario
- [ ] Webhook secret (`WEBHOOK_SECRET`) is set to a real value, not `change-me`
