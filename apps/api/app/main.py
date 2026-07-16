from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import AppError, to_http_exception
from app.db.session import AsyncSessionLocal
from app.services.auth import sync_system_role_permissions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        async with AsyncSessionLocal() as session:
            await sync_system_role_permissions(session)
            await session.commit()
    except Exception:
        # DB may be unavailable at import/test time; migrations handle schema.
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.8.0",
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
        "version": "0.8.0",
    }


app.include_router(api_router, prefix=settings.api_v1_prefix)
