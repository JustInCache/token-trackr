"""
Azure OpenAI Wrapper
====================
Wrapper for Azure OpenAI client with automatic token tracking.
"""

import time
from collections.abc import Iterator
from typing import Any, Optional

from token_trackr.client import TokenTrackrClient, get_client


class AzureOpenAIWrapper:
    """
    Wrapper for Azure OpenAI client that automatically tracks token usage.

    Usage:
        from openai import AzureOpenAI
        from token_trackr import AzureOpenAIWrapper

        azure_client = AzureOpenAI(
            api_key="your-key",
            api_version="2024-02-01",
            azure_endpoint="https://your-resource.openai.azure.com",
        )
        wrapper = AzureOpenAIWrapper(azure_client)

        response = wrapper.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello!"}],
        )
    """

    def __init__(
        self,
        azure_client: Any,
        client: Optional[TokenTrackrClient] = None,
    ):
        """
        Initialize the Azure OpenAI wrapper.

        Args:
            azure_client: OpenAI AzureOpenAI client
            client: Token Trackr client (uses global if not provided)
        """
        self._azure = azure_client
        self._client = client or get_client()

        # Create wrapped interfaces
        self.chat = _ChatWrapper(self._azure.chat, self._client)
        self.completions = _CompletionsWrapper(self._azure.completions, self._client)
        self.embeddings = _EmbeddingsWrapper(self._azure.embeddings, self._client)

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the underlying Azure client."""
        return getattr(self._azure, name)


class _ChatWrapper:
    """Wrapper for chat completions."""

    def __init__(self, chat: Any, client: TokenTrackrClient):
        self._chat = chat
        self._client = client
        self.completions = _ChatCompletionsWrapper(chat.completions, client)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class _ChatCompletionsWrapper:
    """Wrapper for chat.completions with token tracking."""

    def __init__(self, completions: Any, client: TokenTrackrClient):
        self._completions = completions
        self._client = client

    def create(
        self,
        model: str,
        messages: list[dict[str, Any]],
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        """
        Create a chat completion with token tracking.
        """
        start_time = time.time()

        response = self._completions.create(
            model=model,
            messages=messages,
            stream=stream,
            **kwargs,
        )

        if stream:
            return _StreamingChatWrapper(
                response=response,
                model=model,
                client=self._client,
                start_time=start_time,
            )

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract token usage
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        # Record usage
        self._client.record(
            provider="azure_openai",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            metadata={
                "id": response.id,
                "finish_reason": response.choices[0].finish_reason if response.choices else None,
            },
        )

        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._completions, name)


class _StreamingChatWrapper:
    """Wrapper for streaming chat responses."""

    def __init__(
        self,
        response: Iterator[Any],
        model: str,
        client: TokenTrackrClient,
        start_time: float,
    ):
        self._response = response
        self._model = model
        self._client = client
        self._start_time = start_time
        self._prompt_tokens = 0
        self._completion_tokens = 0

    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = next(self._response)

            # Track usage from stream options (if available)
            if hasattr(chunk, "usage") and chunk.usage:
                self._prompt_tokens = chunk.usage.prompt_tokens or 0
                self._completion_tokens = chunk.usage.completion_tokens or 0

            return chunk

        except StopIteration:
            # Record usage when stream ends
            latency_ms = int((time.time() - self._start_time) * 1000)
            self._client.record(
                provider="azure_openai",
                model=self._model,
                prompt_tokens=self._prompt_tokens,
                completion_tokens=self._completion_tokens,
                latency_ms=latency_ms,
            )
            raise


class _CompletionsWrapper:
    """Wrapper for legacy completions."""

    def __init__(self, completions: Any, client: TokenTrackrClient):
        self._completions = completions
        self._client = client

    def create(self, model: str, prompt: str, **kwargs: Any) -> Any:
        start_time = time.time()

        response = self._completions.create(
            model=model,
            prompt=prompt,
            **kwargs,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        usage = response.usage
        self._client.record(
            provider="azure_openai",
            model=model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
        )

        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._completions, name)


class _EmbeddingsWrapper:
    """Wrapper for embeddings."""

    def __init__(self, embeddings: Any, client: TokenTrackrClient):
        self._embeddings = embeddings
        self._client = client

    def create(self, model: str, input: str | list[str], **kwargs: Any) -> Any:
        start_time = time.time()

        response = self._embeddings.create(
            model=model,
            input=input,
            **kwargs,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        usage = response.usage
        self._client.record(
            provider="azure_openai",
            model=model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=0,  # Embeddings don't have completion tokens
            latency_ms=latency_ms,
        )

        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._embeddings, name)
