from fastapi import APIRouter

from app.api.v1 import (
    ai,
    auth,
    beneficiaries,
    dashboard,
    finance,
    insights,
    meal,
    organizations,
    platform,
    programs,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(dashboard.router)
api_router.include_router(programs.router)
api_router.include_router(finance.router)
api_router.include_router(meal.router)
api_router.include_router(beneficiaries.router)
api_router.include_router(insights.router)
api_router.include_router(ai.router)
api_router.include_router(platform.router)
