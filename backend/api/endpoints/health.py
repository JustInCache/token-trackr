"""
Health Check Endpoints
======================
Liveness and readiness probes for Kubernetes.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    status: str
    database: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Liveness probe endpoint.
    Returns OK if the service is running.
    """
    return HealthResponse(status="ok", version="1.0.0")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(
    session: AsyncSession = Depends(get_session),
) -> ReadinessResponse:
    """
    Readiness probe endpoint.
    Checks database connectivity.
    """
    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return ReadinessResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        version="1.0.0",
    )
