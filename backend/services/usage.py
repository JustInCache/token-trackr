"""
Usage Service
=============
Business logic for recording and querying token usage.
"""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.pricing import get_pricing_engine
from backend.models.usage import (
    TenantDailySummary,
    TenantMonthlySummary,
    TokenUsageRaw,
)
from backend.schemas.usage import (
    DailySummaryResponse,
    DailyUsageItem,
    HostMetadata,
    MonthlySummaryItem,
    MonthlySummaryResponse,
    TenantSummaryResponse,
    UsageEvent,
)

logger = structlog.get_logger()


class UsageService:
    """Service for managing token usage data."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.pricing = get_pricing_engine()

    async def record_usage(self, event: UsageEvent) -> TokenUsageRaw:
        """
        Record a token usage event.

        Calculates cost and stores the event with full metadata.
        """
        # Calculate cost
        calculated_cost = self.pricing.calculate_cost(
            provider=event.provider,
            model=event.model,
            prompt_tokens=event.prompt_tokens,
            completion_tokens=event.completion_tokens,
            tenant_id=event.tenant_id,
        )

        # Extract host metadata
        host = event.host or HostMetadata()
        k8s = host.k8s

        # Create usage record
        usage = TokenUsageRaw(
            tenant_id=event.tenant_id,
            provider=event.provider,
            model=event.model,
            prompt_tokens=event.prompt_tokens,
            completion_tokens=event.completion_tokens,
            total_tokens=event.prompt_tokens + event.completion_tokens,
            calculated_cost=calculated_cost,
            timestamp=event.timestamp,
            latency_ms=event.latency_ms,
            cloud_provider=host.cloud_provider,
            hostname=host.hostname,
            instance_id=host.instance_id,
            k8s_pod=k8s.pod if k8s else None,
            k8s_namespace=k8s.namespace if k8s else None,
            k8s_node=k8s.node if k8s else None,
            metadata_json=json.dumps(event.metadata) if event.metadata else None,
        )

        self.session.add(usage)
        await self.session.flush()
        await self.session.refresh(usage)

        logger.info(
            "Recorded usage event",
            tenant_id=event.tenant_id,
            provider=event.provider,
            model=event.model,
            tokens=usage.total_tokens,
            cost=float(calculated_cost),
        )

        return usage

    async def get_tenant_summary(self, tenant_id: str) -> TenantSummaryResponse:
        """Get overall usage summary for a tenant."""
        # Get aggregate stats
        stmt = select(
            func.count(TokenUsageRaw.id).label("total_requests"),
            func.sum(TokenUsageRaw.prompt_tokens).label("total_prompt_tokens"),
            func.sum(TokenUsageRaw.completion_tokens).label("total_completion_tokens"),
            func.sum(TokenUsageRaw.total_tokens).label("total_tokens"),
            func.sum(TokenUsageRaw.calculated_cost).label("total_cost"),
            func.min(TokenUsageRaw.timestamp).label("first_usage"),
            func.max(TokenUsageRaw.timestamp).label("last_usage"),
        ).where(TokenUsageRaw.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        row = result.one()

        # Get breakdown by provider
        by_provider = await self._get_breakdown(tenant_id, "provider")
        by_model = await self._get_breakdown(tenant_id, "model")
        by_cloud = await self._get_breakdown(tenant_id, "cloud_provider")

        return TenantSummaryResponse(
            tenant_id=tenant_id,
            total_requests=row.total_requests or 0,
            total_prompt_tokens=row.total_prompt_tokens or 0,
            total_completion_tokens=row.total_completion_tokens or 0,
            total_tokens=row.total_tokens or 0,
            total_cost=row.total_cost or Decimal("0"),
            first_usage=row.first_usage,
            last_usage=row.last_usage,
            by_provider=by_provider,
            by_model=by_model,
            by_cloud_provider=by_cloud,
        )

    async def _get_breakdown(
        self,
        tenant_id: str,
        group_by: str,
    ) -> dict[str, dict[str, Any]]:
        """Get usage breakdown by a specific dimension."""
        column = getattr(TokenUsageRaw, group_by)

        stmt = (
            select(
                column,
                func.count(TokenUsageRaw.id).label("requests"),
                func.sum(TokenUsageRaw.total_tokens).label("tokens"),
                func.sum(TokenUsageRaw.calculated_cost).label("cost"),
            )
            .where(TokenUsageRaw.tenant_id == tenant_id)
            .group_by(column)
        )

        result = await self.session.execute(stmt)

        breakdown = {}
        for row in result:
            key = getattr(row, group_by)
            breakdown[key] = {
                "requests": row.requests,
                "tokens": row.tokens or 0,
                "cost": float(row.cost or 0),
            }

        return breakdown

    async def get_daily_summary(
        self,
        tenant_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> DailySummaryResponse:
        """Get daily usage summary for a tenant."""
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Query pre-aggregated daily summary
        stmt = (
            select(TenantDailySummary)
            .where(
                TenantDailySummary.tenant_id == tenant_id,
                TenantDailySummary.date >= start_date,
                TenantDailySummary.date <= end_date,
            )
            .order_by(TenantDailySummary.date.desc())
        )

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        items = [
            DailyUsageItem(
                date=row.date,
                provider=row.provider,
                model=row.model,
                cloud_provider=row.cloud_provider,
                total_requests=row.total_requests,
                total_prompt_tokens=row.total_prompt_tokens,
                total_completion_tokens=row.total_completion_tokens,
                total_tokens=row.total_tokens,
                total_cost=row.total_cost,
                avg_latency_ms=row.avg_latency_ms,
            )
            for row in rows
        ]

        total_cost = sum(item.total_cost for item in items)
        total_tokens = sum(item.total_tokens for item in items)

        return DailySummaryResponse(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            items=items,
            total_cost=total_cost,
            total_tokens=total_tokens,
        )

    async def get_monthly_summary(
        self,
        tenant_id: str,
        year: int | None = None,
        month: int | None = None,
    ) -> MonthlySummaryResponse:
        """Get monthly usage summary for a tenant."""
        stmt = select(TenantMonthlySummary).where(TenantMonthlySummary.tenant_id == tenant_id)

        if year:
            stmt = stmt.where(TenantMonthlySummary.year == year)
        if month:
            stmt = stmt.where(TenantMonthlySummary.month == month)

        stmt = stmt.order_by(
            TenantMonthlySummary.year.desc(),
            TenantMonthlySummary.month.desc(),
        )

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        items = [
            MonthlySummaryItem(
                year=row.year,
                month=row.month,
                provider=row.provider,
                model=row.model,
                total_requests=row.total_requests,
                total_prompt_tokens=row.total_prompt_tokens,
                total_completion_tokens=row.total_completion_tokens,
                total_tokens=row.total_tokens,
                total_cost=row.total_cost,
            )
            for row in rows
        ]

        total_cost = sum(item.total_cost for item in items)
        total_tokens = sum(item.total_tokens for item in items)

        return MonthlySummaryResponse(
            tenant_id=tenant_id,
            items=items,
            total_cost=total_cost,
            total_tokens=total_tokens,
        )

    async def get_raw_usage(
        self,
        tenant_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[TokenUsageRaw]:
        """Get raw usage events for a tenant."""
        stmt = select(TokenUsageRaw).where(TokenUsageRaw.tenant_id == tenant_id)

        if start_time:
            stmt = stmt.where(TokenUsageRaw.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(TokenUsageRaw.timestamp <= end_time)

        stmt = stmt.order_by(TokenUsageRaw.timestamp.desc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
