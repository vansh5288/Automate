import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.routes import requests as requests_routes
from app.routes import webhooks as webhooks_routes
from app.workers.notion_poller import poll_loop

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("procureflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    poller_task = asyncio.create_task(poll_loop())
    logger.info("ProcureFlow backend started (env=%s)", settings.app_env)
    yield
    poller_task.cancel()


app = FastAPI(title="ProcureFlow", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}


app.include_router(requests_routes.router)
app.include_router(webhooks_routes.router)
