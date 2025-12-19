"""
Token Trackr Client
=====================
Main client for sending usage events to the backend.
"""

import asyncio
import atexit
import json
import logging
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from token_trackr.config import TokenTrackrConfig
from token_trackr.metadata import HostMetadata, get_host_metadata
from token_trackr.models import UsageEvent, UsageResponse

logger = logging.getLogger(__name__)


class TokenTrackrClient:
    """
    Client for sending token usage events to the Token Trackr backend.
    
    Features:
    - Async non-blocking event sending
    - Local queue with fallback for network failures
    - Automatic batching and flushing
    - Retry with exponential backoff
    """
    
    def __init__(
        self,
        config: Optional[TokenTrackrConfig] = None,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize the Token Trackr client.
        
        Args:
            config: Configuration object (uses defaults if not provided)
            tenant_id: Override tenant ID from config
        """
        self.config = config or TokenTrackrConfig()
        if tenant_id:
            self.config.tenant_id = tenant_id
        
        # Initialize host metadata (cached)
        self._host_metadata: Optional[HostMetadata] = None
        
        # Event queue for batching
        self._queue: Deque[UsageEvent] = deque(maxlen=self.config.max_queue_size)
        self._lock = threading.Lock()
        
        # HTTP client
        self._client = httpx.Client(
            base_url=self.config.backend_url,
            timeout=self.config.timeout,
            headers=self._get_headers(),
        )
        
        # Background flush thread
        self._stop_event = threading.Event()
        self._flush_thread: Optional[threading.Thread] = None
        
        if self.config.async_mode:
            self._start_background_flush()
        
        # Register cleanup on exit
        atexit.register(self.close)
    
    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "token-trackr-sdk-python/1.0.0",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers
    
    @property
    def host_metadata(self) -> HostMetadata:
        """Get cached host metadata."""
        if self._host_metadata is None:
            self._host_metadata = get_host_metadata()
        return self._host_metadata
    
    def _start_background_flush(self) -> None:
        """Start background thread for periodic flushing."""
        def flush_worker():
            while not self._stop_event.is_set():
                time.sleep(self.config.flush_interval)
                try:
                    self.flush()
                except Exception as e:
                    logger.error(f"Background flush failed: {e}")
        
        self._flush_thread = threading.Thread(target=flush_worker, daemon=True)
        self._flush_thread.start()
    
    def record(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record a token usage event.
        
        Args:
            provider: LLM provider (bedrock, azure_openai, gemini)
            model: Model identifier
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            latency_ms: Request latency in milliseconds
            metadata: Additional metadata
            timestamp: Event timestamp (defaults to now)
        """
        event = UsageEvent(
            tenant_id=self.config.tenant_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            timestamp=timestamp or datetime.utcnow(),
            latency_ms=latency_ms,
            host=self.host_metadata.to_dict(),
            metadata=metadata,
        )
        
        with self._lock:
            self._queue.append(event)
        
        # Flush if batch size reached
        if len(self._queue) >= self.config.batch_size:
            if self.config.async_mode:
                threading.Thread(target=self.flush, daemon=True).start()
            else:
                self.flush()
    
    def flush(self) -> list[UsageResponse]:
        """
        Flush all queued events to the backend.
        
        Returns:
            List of responses from the backend
        """
        with self._lock:
            if not self._queue:
                return []
            
            events = list(self._queue)
            self._queue.clear()
        
        try:
            return self._send_batch(events)
        except Exception as e:
            logger.error(f"Failed to send events: {e}")
            # Put events back in queue for retry
            with self._lock:
                for event in events:
                    if len(self._queue) < self.config.max_queue_size:
                        self._queue.appendleft(event)
            # Save to local fallback
            self._save_to_fallback(events)
            return []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    def _send_batch(self, events: list[UsageEvent]) -> list[UsageResponse]:
        """Send a batch of events to the backend with retry."""
        if len(events) == 1:
            response = self._client.post(
                "/usage",
                json=events[0].model_dump(mode="json"),
            )
        else:
            response = self._client.post(
                "/usage/batch",
                json=[e.model_dump(mode="json") for e in events],
            )
        
        response.raise_for_status()
        
        data = response.json()
        if isinstance(data, list):
            return [UsageResponse(**item) for item in data]
        return [UsageResponse(**data)]
    
    def _save_to_fallback(self, events: list[UsageEvent]) -> None:
        """Save events to local file as fallback."""
        fallback_dir = Path.home() / ".token-trackr" / "fallback"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        
        fallback_file = fallback_dir / f"events_{int(time.time())}.json"
        
        try:
            with open(fallback_file, "w") as f:
                json.dump([e.model_dump(mode="json") for e in events], f)
            logger.info(f"Saved {len(events)} events to fallback: {fallback_file}")
        except Exception as e:
            logger.error(f"Failed to save fallback: {e}")
    
    def close(self) -> None:
        """Close the client and flush remaining events."""
        self._stop_event.set()
        
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5)
        
        # Final flush
        try:
            self.flush()
        except Exception as e:
            logger.error(f"Final flush failed: {e}")
        
        self._client.close()
    
    def __enter__(self) -> "TokenTrackrClient":
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.close()


# Global client instance
_global_client: Optional[TokenTrackrClient] = None


def get_client() -> TokenTrackrClient:
    """Get or create the global client instance."""
    global _global_client
    if _global_client is None:
        _global_client = TokenTrackrClient()
    return _global_client


def record(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    **kwargs: Any,
) -> None:
    """Record a usage event using the global client."""
    get_client().record(
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        **kwargs,
    )

