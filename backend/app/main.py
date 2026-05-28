import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import _run_refresh, router
from .config import settings
from .db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("gitinvest")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.refresh_hour is not None:
        scheduler.add_job(
            _run_refresh,
            CronTrigger(hour=settings.refresh_hour, minute=0),
            kwargs={"min_stars": None, "max_stars": None},
            id="daily_refresh",
            replace_existing=True,
        )
        scheduler.start()
        log.info("scheduler started; daily refresh at %02d:00", settings.refresh_hour)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="GitInvest API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "token_configured": bool(settings.github_token)}
