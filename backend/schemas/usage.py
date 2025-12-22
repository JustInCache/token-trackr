"""
Usage Schemas
=============
Pydantic models for usage tracking API.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class K8sMetadata(BaseModel):
    """Kubernetes metadata from the SDK."""

    pod: str | None = None
    namespace: str | None = None
    node: str | None = None


class HostMetadata(BaseModel):
    """Host metadata from the SDK."""

    hostname: str | None = None
    cloud_provider: str = Field(default="unknown", pattern="^(aws|azure|gcp|on-prem|unknown)$")
    instance_id: str | None = None
    k8s: K8sMetadata | None = None


class UsageEvent(BaseModel):
    """
    Token usage event sent from SDK.
    Represents a single LLM API call.
    """

    tenant_id: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., pattern="^(bedrock|azure_openai|gemini)$")
    model: str = Field(..., min_length=1, max_length=255)
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    timestamp: datetime
    latency_ms: int | None = Field(default=None, ge=0)
    host: HostMetadata | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class UsageEventResponse(BaseModel):
    """Response after recording usage event."""

    id: UUID
    tenant_id: str
    provider: str
    model: str
    total_tokens: int
    calculated_cost: Decimal
    timestamp: datetime

    class Config:
        from_attributes = True


class DailyUsageItem(BaseModel):
    """Single day usage breakdown."""

    date: date
    provider: str
    model: str
    cloud_provider: str
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost: Decimal
    avg_latency_ms: int | None = None


class DailySummaryResponse(BaseModel):
    """Daily usage summary for a tenant."""

    tenant_id: str
    start_date: date
    end_date: date
    items: list[DailyUsageItem]
    total_cost: Decimal
    total_tokens: int


class MonthlySummaryItem(BaseModel):
    """Single month usage breakdown."""

    year: int
    month: int
    provider: str
    model: str
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost: Decimal


class MonthlySummaryResponse(BaseModel):
    """Monthly usage summary for a tenant."""

    tenant_id: str
    items: list[MonthlySummaryItem]
    total_cost: Decimal
    total_tokens: int


class TenantSummaryResponse(BaseModel):
    """Overall summary for a tenant."""

    tenant_id: str
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost: Decimal
    first_usage: datetime | None = None
    last_usage: datetime | None = None
    by_provider: dict[str, dict[str, Any]]
    by_model: dict[str, dict[str, Any]]
    by_cloud_provider: dict[str, dict[str, Any]]


class ModelPricing(BaseModel):
    """Pricing information for a model."""

    model: str
    input_price_per_1k: Decimal
    output_price_per_1k: Decimal


class ProviderModelsResponse(BaseModel):
    """Available models and pricing for a provider."""

    provider: str
    models: list[ModelPricing]
