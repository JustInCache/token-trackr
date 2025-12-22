"""
Usage Endpoints
===============
API endpoints for recording token usage events.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.schemas.usage import UsageEvent, UsageEventResponse
from backend.services.usage import UsageService

router = APIRouter()
logger = structlog.get_logger()


@router.post(
    "",
    response_model=UsageEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record token usage",
    description="Record a token usage event from the SDK",
)
async def record_usage(
    event: UsageEvent,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UsageEventResponse:
    """
    Record a token usage event.

    This endpoint receives usage data from the SDK and:
    - Validates the event data
    - Auto-detects the source (K8s, EC2, GCE, Azure VM)
    - Calculates the cost based on model pricing
    - Stores the event in the database
    """
    try:
        service = UsageService(session)
        usage = await service.record_usage(event)

        return UsageEventResponse(
            id=usage.id,
            tenant_id=usage.tenant_id,
            provider=usage.provider,
            model=usage.model,
            total_tokens=usage.total_tokens,
            calculated_cost=usage.calculated_cost,
            timestamp=usage.timestamp,
        )
    except ValueError as e:
        logger.warning("Invalid usage event", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Failed to record usage", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record usage event",
        ) from e


@router.post(
    "/batch",
    response_model=list[UsageEventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Record multiple usage events",
    description="Record multiple token usage events in a single request",
)
async def record_usage_batch(
    events: list[UsageEvent],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[UsageEventResponse]:
    """
    Record multiple token usage events in batch.

    Useful for SDKs that queue events locally and send them periodically.
    """
    if len(events) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum batch size is 1000 events",
        )

    service = UsageService(session)
    results = []

    for event in events:
        try:
            usage = await service.record_usage(event)
            results.append(
                UsageEventResponse(
                    id=usage.id,
                    tenant_id=usage.tenant_id,
                    provider=usage.provider,
                    model=usage.model,
                    total_tokens=usage.total_tokens,
                    calculated_cost=usage.calculated_cost,
                    timestamp=usage.timestamp,
                )
            )
        except Exception as e:
            logger.warning("Failed to record event in batch", error=str(e))
            continue

    return results
