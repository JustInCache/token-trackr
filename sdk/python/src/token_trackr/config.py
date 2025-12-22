"""
SDK Configuration
=================
Configuration management for the Token Trackr SDK.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenTrackrConfig:
    """
    Configuration for the Token Trackr SDK.

    Attributes:
        backend_url: URL of the Token Trackr backend
        api_key: API key for authentication
        tenant_id: Tenant identifier for multi-tenancy
        batch_size: Number of events to batch before sending
        flush_interval: Seconds between automatic flushes
        max_queue_size: Maximum events to queue locally
        retry_attempts: Number of retry attempts for failed requests
        timeout: Request timeout in seconds
        async_mode: Enable non-blocking event sending
    """

    backend_url: str = field(
        default_factory=lambda: os.getenv("TOKEN_TRACKR_URL", "http://localhost:8000")
    )
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("TOKEN_TRACKR_API_KEY"))
    tenant_id: str = field(default_factory=lambda: os.getenv("TOKEN_TRACKR_TENANT_ID", "default"))
    batch_size: int = 10
    flush_interval: float = 5.0
    max_queue_size: int = 1000
    retry_attempts: int = 3
    timeout: float = 30.0
    async_mode: bool = True

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.backend_url:
            raise ValueError("backend_url is required")
        if not self.tenant_id:
            raise ValueError("tenant_id is required")

        # Ensure URL doesn't end with slash
        self.backend_url = self.backend_url.rstrip("/")
