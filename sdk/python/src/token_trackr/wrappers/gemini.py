"""
Google Gemini Wrapper
=====================
Wrapper for Google Gemini client with automatic token tracking.
"""

import time
from typing import Any, Iterator, Optional

from token_trackr.client import TokenTrackrClient, get_client


class GeminiWrapper:
    """
    Wrapper for Google Gemini client that automatically tracks token usage.
    
    Usage:
        import google.generativeai as genai
        from token_trackr import GeminiWrapper
        
        genai.configure(api_key="your-key")
        model = genai.GenerativeModel("gemini-1.5-pro")
        wrapper = GeminiWrapper(model)
        
        response = wrapper.generate_content("Hello!")
    """
    
    def __init__(
        self,
        model: Any,
        client: Optional[TokenTrackrClient] = None,
    ):
        """
        Initialize the Gemini wrapper.
        
        Args:
            model: google.generativeai GenerativeModel instance
            client: Token Trackr client (uses global if not provided)
        """
        self._model = model
        self._client = client or get_client()
        self._model_name = getattr(model, "model_name", "gemini-unknown")
    
    def generate_content(
        self,
        contents: Any,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        """
        Generate content with token tracking.
        
        Args:
            contents: The input content (text, list of parts, etc.)
            stream: Whether to stream the response
            **kwargs: Additional arguments for generate_content
            
        Returns:
            The model response
        """
        start_time = time.time()
        
        if stream:
            response = self._model.generate_content(
                contents,
                stream=True,
                **kwargs,
            )
            return _StreamingGeminiWrapper(
                response=response,
                model_name=self._model_name,
                client=self._client,
                start_time=start_time,
            )
        
        response = self._model.generate_content(contents, **kwargs)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Extract token usage
        prompt_tokens, completion_tokens = self._extract_tokens(response)
        
        # Record usage
        self._client.record(
            provider="gemini",
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            metadata={
                "finish_reason": self._get_finish_reason(response),
            },
        )
        
        return response
    
    def generate_content_async(
        self,
        contents: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Async content generation with token tracking.
        """
        import asyncio
        
        async def _generate():
            start_time = time.time()
            
            response = await self._model.generate_content_async(contents, **kwargs)
            
            latency_ms = int((time.time() - start_time) * 1000)
            prompt_tokens, completion_tokens = self._extract_tokens(response)
            
            self._client.record(
                provider="gemini",
                model=self._model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
            )
            
            return response
        
        return _generate()
    
    def count_tokens(self, contents: Any) -> Any:
        """
        Count tokens in content (no usage tracking for this).
        """
        return self._model.count_tokens(contents)
    
    def start_chat(self, **kwargs: Any) -> "_ChatSessionWrapper":
        """
        Start a chat session with token tracking.
        """
        chat = self._model.start_chat(**kwargs)
        return _ChatSessionWrapper(
            chat=chat,
            model_name=self._model_name,
            client=self._client,
        )
    
    def _extract_tokens(self, response: Any) -> tuple[int, int]:
        """Extract token counts from response."""
        try:
            usage = response.usage_metadata
            return (
                usage.prompt_token_count,
                usage.candidates_token_count,
            )
        except AttributeError:
            return (0, 0)
    
    def _get_finish_reason(self, response: Any) -> Optional[str]:
        """Get finish reason from response."""
        try:
            if response.candidates:
                return str(response.candidates[0].finish_reason)
        except Exception:
            pass
        return None
    
    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the underlying model."""
        return getattr(self._model, name)


class _StreamingGeminiWrapper:
    """Wrapper for streaming Gemini responses."""
    
    def __init__(
        self,
        response: Iterator[Any],
        model_name: str,
        client: TokenTrackrClient,
        start_time: float,
    ):
        self._response = response
        self._model_name = model_name
        self._client = client
        self._start_time = start_time
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._chunks: list[Any] = []
    
    def __iter__(self):
        return self
    
    def __next__(self):
        try:
            chunk = next(self._response)
            self._chunks.append(chunk)
            
            # Update token counts from usage metadata
            try:
                usage = chunk.usage_metadata
                self._prompt_tokens = usage.prompt_token_count
                self._completion_tokens = usage.candidates_token_count
            except AttributeError:
                pass
            
            return chunk
            
        except StopIteration:
            # Record usage when stream ends
            latency_ms = int((time.time() - self._start_time) * 1000)
            self._client.record(
                provider="gemini",
                model=self._model_name,
                prompt_tokens=self._prompt_tokens,
                completion_tokens=self._completion_tokens,
                latency_ms=latency_ms,
            )
            raise


class _ChatSessionWrapper:
    """Wrapper for Gemini chat sessions."""
    
    def __init__(
        self,
        chat: Any,
        model_name: str,
        client: TokenTrackrClient,
    ):
        self._chat = chat
        self._model_name = model_name
        self._client = client
    
    def send_message(
        self,
        content: Any,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Send a message with token tracking."""
        start_time = time.time()
        
        if stream:
            response = self._chat.send_message(content, stream=True, **kwargs)
            return _StreamingGeminiWrapper(
                response=response,
                model_name=self._model_name,
                client=self._client,
                start_time=start_time,
            )
        
        response = self._chat.send_message(content, **kwargs)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        try:
            usage = response.usage_metadata
            prompt_tokens = usage.prompt_token_count
            completion_tokens = usage.candidates_token_count
        except AttributeError:
            prompt_tokens = 0
            completion_tokens = 0
        
        self._client.record(
            provider="gemini",
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
        
        return response
    
    @property
    def history(self):
        return self._chat.history
    
    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)

