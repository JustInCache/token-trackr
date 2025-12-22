"""
API Router
==========
Main API router combining all endpoint modules.
"""

from fastapi import APIRouter

from backend.api.endpoints import health, providers, tenants, usage

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(usage.router, prefix="/usage", tags=["Usage"])
api_router.include_router(tenants.router, prefix="/tenant", tags=["Tenants"])
api_router.include_router(providers.router, prefix="/provider", tags=["Providers"])
