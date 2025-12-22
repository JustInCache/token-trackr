"""
Token Usage Models
==================
Models for tracking token usage, costs, and pricing.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Date,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class TokenUsageRaw(Base, TimestampMixin):
    """
    Raw token usage events.
    Stores every individual LLM API call with full metadata.
    """

    __tablename__ = "token_usage_raw"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    prompt_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    calculated_cost: Mapped[Decimal] = mapped_column(
        Numeric(20, 10),
        nullable=False,
        default=Decimal("0"),
    )
    timestamp: Mapped[datetime] = mapped_column(nullable=False, index=True)
    latency_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Host metadata
    cloud_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
    )
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instance_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Kubernetes metadata
    k8s_pod: Mapped[str | None] = mapped_column(String(255), nullable=True)
    k8s_namespace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    k8s_node: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Additional metadata as JSON string
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_usage_tenant_timestamp", "tenant_id", "timestamp"),
        Index("idx_usage_provider_model", "provider", "model"),
        Index("idx_usage_cloud_instance", "cloud_provider", "instance_id"),
        Index("idx_usage_k8s", "k8s_namespace", "k8s_pod"),
    )


class TenantDailySummary(Base, TimestampMixin):
    """
    Daily aggregated token usage per tenant.
    Pre-computed for fast dashboard queries.
    """

    __tablename__ = "tenant_daily_summary"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    cloud_provider: Mapped[str] = mapped_column(String(50), nullable=False)

    # Aggregated metrics
    total_requests: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_prompt_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_completion_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(20, 10),
        nullable=False,
        default=Decimal("0"),
    )
    avg_latency_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "date", "provider", "model", "cloud_provider", name="uq_daily_summary"
        ),
        Index("idx_daily_tenant_date", "tenant_id", "date"),
    )


class TenantMonthlySummary(Base, TimestampMixin):
    """
    Monthly aggregated token usage per tenant.
    Used for billing and high-level reporting.
    """

    __tablename__ = "tenant_monthly_summary"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    month: Mapped[int] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)

    # Aggregated metrics
    total_requests: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_prompt_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_completion_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(20, 10),
        nullable=False,
        default=Decimal("0"),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "year", "month", "provider", "model", name="uq_monthly_summary"
        ),
        Index("idx_monthly_tenant_period", "tenant_id", "year", "month"),
    )


class PricingTable(Base, TimestampMixin):
    """
    Dynamic pricing configuration.
    Allows runtime updates without config file changes.
    """

    __tablename__ = "pricing_table"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    input_price_per_1k: Mapped[Decimal] = mapped_column(
        Numeric(20, 10),
        nullable=False,
    )
    output_price_per_1k: Mapped[Decimal] = mapped_column(
        Numeric(20, 10),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (
        UniqueConstraint("provider", "model", "effective_from", name="uq_pricing_model_date"),
        Index("idx_pricing_lookup", "provider", "model", "is_active"),
    )
