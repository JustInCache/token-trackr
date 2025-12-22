"""
Tenant Endpoints
================
API endpoints for tenant usage reports and summaries.
"""

from datetime import date
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.schemas.usage import (
    DailySummaryResponse,
    MonthlySummaryResponse,
    TenantSummaryResponse,
)
from backend.services.usage import UsageService

router = APIRouter()
logger = structlog.get_logger()


@router.get(
    "/{tenant_id}/summary",
    response_model=TenantSummaryResponse,
    summary="Get tenant usage summary",
    description="Get overall usage summary for a tenant including breakdowns by provider, model, and cloud",
)
async def get_tenant_summary(
    tenant_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TenantSummaryResponse:
    """
    Get overall usage summary for a tenant.

    Returns:
    - Total requests, tokens, and cost
    - First and last usage timestamps
    - Breakdown by provider, model, and cloud provider
    """
    try:
        service = UsageService(session)
        return await service.get_tenant_summary(tenant_id)
    except Exception as e:
        logger.error("Failed to get tenant summary", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant summary",
        ) from e


@router.get(
    "/{tenant_id}/daily",
    response_model=DailySummaryResponse,
    summary="Get daily usage summary",
    description="Get daily aggregated usage for a tenant",
)
async def get_daily_summary(
    tenant_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    start_date: Annotated[date | None, Query(description="Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[date | None, Query(description="End date (YYYY-MM-DD)")] = None,
) -> DailySummaryResponse:
    """
    Get daily usage summary for a tenant.

    Defaults to last 30 days if no date range specified.
    """
    try:
        service = UsageService(session)
        return await service.get_daily_summary(tenant_id, start_date, end_date)
    except Exception as e:
        logger.error("Failed to get daily summary", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve daily summary",
        ) from e


@router.get(
    "/{tenant_id}/monthly",
    response_model=MonthlySummaryResponse,
    summary="Get monthly usage summary",
    description="Get monthly aggregated usage for a tenant",
)
async def get_monthly_summary(
    tenant_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    year: Annotated[int | None, Query(description="Filter by year", ge=2020, le=2100)] = None,
    month: Annotated[int | None, Query(description="Filter by month", ge=1, le=12)] = None,
) -> MonthlySummaryResponse:
    """
    Get monthly usage summary for a tenant.

    Optionally filter by year and/or month.
    """
    try:
        service = UsageService(session)
        return await service.get_monthly_summary(tenant_id, year, month)
    except Exception as e:
        logger.error("Failed to get monthly summary", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monthly summary",
        ) from e
