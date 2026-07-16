from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import AppError, to_http_exception
from app.core.secrets import validate_runtime_secrets
from app.db.session import AsyncSessionLocal
from app.services.auth import sync_system_role_permissions
from app.services import jobs as jobs_service
from app.services.rate_limit import get_redis

logger = logging.getLogger(__name__)

API_VERSION = "0.16.0"


async def _jobs_loop(stop: asyncio.Event) -> None:
    interval = max(10, int(getattr(settings, "jobs_poll_seconds", 30) or 30))
    while not stop.is_set():
        try:
            result = await jobs_service.run_job_tick()
            if result.get("webhooks_processed") or result.get("overdue_tasks_notified"):
                logger.info("jobs.tick %s", result)
        except Exception:  # noqa: BLE001
            logger.exception("jobs.tick_failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_runtime_secrets()
    try:
        async with AsyncSessionLocal() as session:
            await sync_system_role_permissions(session)
            await session.commit()
    except Exception:
        # DB may be unavailable at import/test time; migrations handle schema.
        pass

    stop = asyncio.Event()
    task = None
    if settings.jobs_enabled and not settings.app_env.lower().startswith("test"):
        task = asyncio.create_task(_jobs_loop(stop), name="impactflow-jobs")
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title=settings.app_name,
    version=API_VERSION,
    description="ImpactFlow AI — Enterprise MEAL & Project Operating System API",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    http_exc = to_http_exception(exc)
    return JSONResponse(status_code=http_exc.status_code, content=http_exc.detail)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": API_VERSION,
    }


@app.get("/ready")
async def ready():
    """Liveness for orchestration: DB + Redis must both respond."""
    checks: dict[str, bool] = {"database": False, "redis": False}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("ready.database_failed: %s", exc)

    try:
        client = await get_redis()
        if client is not None:
            await client.ping()
            checks["redis"] = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("ready.redis_failed: %s", exc)

    ok = checks["database"] and checks["redis"]
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ready" if ok else "not_ready",
            "checks": checks,
            "version": API_VERSION,
        },
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)
