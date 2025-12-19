"""
Aggregation Jobs
================
Daily and monthly token usage aggregation jobs.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.database import get_session_context
from backend.models.usage import (
    TenantDailySummary,
    TenantMonthlySummary,
    TokenUsageRaw,
)

logger = structlog.get_logger()


class DailyAggregationJob:
    """
    Aggregate raw token usage into daily summaries.
    
    Runs daily to pre-compute usage statistics for fast dashboard queries.
    """

    async def run(self, target_date: Optional[date] = None) -> int:
        """
        Run daily aggregation for a specific date.
        
        Args:
            target_date: Date to aggregate (defaults to yesterday)
            
        Returns:
            Number of summary records created/updated
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        logger.info("Starting daily aggregation", date=str(target_date))

        async with get_session_context() as session:
            # Get aggregated data from raw events
            stmt = select(
                TokenUsageRaw.tenant_id,
                TokenUsageRaw.provider,
                TokenUsageRaw.model,
                TokenUsageRaw.cloud_provider,
                func.count(TokenUsageRaw.id).label("total_requests"),
                func.sum(TokenUsageRaw.prompt_tokens).label("total_prompt_tokens"),
                func.sum(TokenUsageRaw.completion_tokens).label("total_completion_tokens"),
                func.sum(TokenUsageRaw.total_tokens).label("total_tokens"),
                func.sum(TokenUsageRaw.calculated_cost).label("total_cost"),
                func.avg(TokenUsageRaw.latency_ms).label("avg_latency_ms"),
            ).where(
                func.date(TokenUsageRaw.timestamp) == target_date
            ).group_by(
                TokenUsageRaw.tenant_id,
                TokenUsageRaw.provider,
                TokenUsageRaw.model,
                TokenUsageRaw.cloud_provider,
            )

            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                logger.info("No data to aggregate", date=str(target_date))
                return 0

            # Upsert daily summaries
            count = 0
            for row in rows:
                upsert_stmt = pg_insert(TenantDailySummary).values(
                    tenant_id=row.tenant_id,
                    date=target_date,
                    provider=row.provider,
                    model=row.model,
                    cloud_provider=row.cloud_provider,
                    total_requests=row.total_requests,
                    total_prompt_tokens=row.total_prompt_tokens or 0,
                    total_completion_tokens=row.total_completion_tokens or 0,
                    total_tokens=row.total_tokens or 0,
                    total_cost=row.total_cost or Decimal("0"),
                    avg_latency_ms=int(row.avg_latency_ms) if row.avg_latency_ms else None,
                ).on_conflict_do_update(
                    constraint="uq_daily_summary",
                    set_={
                        "total_requests": row.total_requests,
                        "total_prompt_tokens": row.total_prompt_tokens or 0,
                        "total_completion_tokens": row.total_completion_tokens or 0,
                        "total_tokens": row.total_tokens or 0,
                        "total_cost": row.total_cost or Decimal("0"),
                        "avg_latency_ms": int(row.avg_latency_ms) if row.avg_latency_ms else None,
                    },
                )
                await session.execute(upsert_stmt)
                count += 1

            await session.commit()
            logger.info("Daily aggregation completed", date=str(target_date), records=count)
            return count

    async def backfill(self, start_date: date, end_date: date) -> int:
        """
        Backfill daily aggregations for a date range.
        """
        total = 0
        current = start_date
        
        while current <= end_date:
            count = await self.run(current)
            total += count
            current += timedelta(days=1)
        
        logger.info("Backfill completed", start=str(start_date), end=str(end_date), total=total)
        return total


class MonthlyAggregationJob:
    """
    Aggregate daily summaries into monthly summaries.
    
    Runs monthly to compute billing totals.
    """

    async def run(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> int:
        """
        Run monthly aggregation.
        
        Args:
            year: Year to aggregate (defaults to previous month)
            month: Month to aggregate (defaults to previous month)
            
        Returns:
            Number of summary records created/updated
        """
        if year is None or month is None:
            # Default to previous month
            today = date.today()
            first_of_month = today.replace(day=1)
            last_month = first_of_month - timedelta(days=1)
            year = last_month.year
            month = last_month.month

        logger.info("Starting monthly aggregation", year=year, month=month)

        async with get_session_context() as session:
            # Get first and last day of the month
            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)

            # Aggregate from daily summaries
            stmt = select(
                TenantDailySummary.tenant_id,
                TenantDailySummary.provider,
                TenantDailySummary.model,
                func.sum(TenantDailySummary.total_requests).label("total_requests"),
                func.sum(TenantDailySummary.total_prompt_tokens).label("total_prompt_tokens"),
                func.sum(TenantDailySummary.total_completion_tokens).label("total_completion_tokens"),
                func.sum(TenantDailySummary.total_tokens).label("total_tokens"),
                func.sum(TenantDailySummary.total_cost).label("total_cost"),
            ).where(
                TenantDailySummary.date >= first_day,
                TenantDailySummary.date <= last_day,
            ).group_by(
                TenantDailySummary.tenant_id,
                TenantDailySummary.provider,
                TenantDailySummary.model,
            )

            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                logger.info("No data to aggregate", year=year, month=month)
                return 0

            # Upsert monthly summaries
            count = 0
            for row in rows:
                upsert_stmt = pg_insert(TenantMonthlySummary).values(
                    tenant_id=row.tenant_id,
                    year=year,
                    month=month,
                    provider=row.provider,
                    model=row.model,
                    total_requests=row.total_requests or 0,
                    total_prompt_tokens=row.total_prompt_tokens or 0,
                    total_completion_tokens=row.total_completion_tokens or 0,
                    total_tokens=row.total_tokens or 0,
                    total_cost=row.total_cost or Decimal("0"),
                ).on_conflict_do_update(
                    constraint="uq_monthly_summary",
                    set_={
                        "total_requests": row.total_requests or 0,
                        "total_prompt_tokens": row.total_prompt_tokens or 0,
                        "total_completion_tokens": row.total_completion_tokens or 0,
                        "total_tokens": row.total_tokens or 0,
                        "total_cost": row.total_cost or Decimal("0"),
                    },
                )
                await session.execute(upsert_stmt)
                count += 1

            await session.commit()
            logger.info("Monthly aggregation completed", year=year, month=month, records=count)
            return count

