"""
Data Models
===========
Pydantic models for SDK data structures.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class UsageEvent(BaseModel):
    """Token usage event to send to the backend."""

    tenant_id: str
    provider: str
    model: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    timestamp: datetime
    latency_ms: Optional[int] = Field(default=None, ge=0)
    host: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class UsageResponse(BaseModel):
    """Response from the backend after recording usage."""

    id: str
    tenant_id: str
    provider: str
    model: str
    total_tokens: int
    calculated_cost: float
    timestamp: datetime
