"""
AWS Bedrock Wrapper
===================
Wrapper for AWS Bedrock client with automatic token tracking.
"""

import json
import time
from typing import Any, Optional

from token_trackr.client import TokenTrackrClient, get_client


class BedrockWrapper:
    """
    Wrapper for AWS Bedrock client that automatically tracks token usage.
    
    Usage:
        import boto3
        from token_trackr import BedrockWrapper
        
        bedrock = boto3.client("bedrock-runtime")
        wrapper = BedrockWrapper(bedrock)
        
        response = wrapper.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps({
                "messages": [{"role": "user", "content": "Hello!"}],
                "max_tokens": 100,
            }),
        )
    """
    
    def __init__(
        self,
        bedrock_client: Any,
        client: Optional[TokenTrackrClient] = None,
    ):
        """
        Initialize the Bedrock wrapper.
        
        Args:
            bedrock_client: boto3 Bedrock Runtime client
            client: Token Trackr client (uses global if not provided)
        """
        self._bedrock = bedrock_client
        self._client = client or get_client()
    
    def invoke_model(
        self,
        modelId: str,
        body: str | bytes,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Invoke a Bedrock model with token tracking.
        
        Args:
            modelId: The model identifier
            body: Request body (JSON string or bytes)
            **kwargs: Additional arguments for invoke_model
            
        Returns:
            The model response
        """
        start_time = time.time()
        
        # Call the actual Bedrock API
        response = self._bedrock.invoke_model(
            modelId=modelId,
            body=body,
            **kwargs,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Parse response body
        response_body = json.loads(response["body"].read())
        
        # Extract token counts based on model family
        prompt_tokens, completion_tokens = self._extract_tokens(
            modelId, response_body, response
        )
        
        # Record usage
        self._client.record(
            provider="bedrock",
            model=modelId,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            metadata={
                "request_id": response.get("ResponseMetadata", {}).get("RequestId"),
            },
        )
        
        return response_body
    
    def invoke_model_with_response_stream(
        self,
        modelId: str,
        body: str | bytes,
        **kwargs: Any,
    ) -> Any:
        """
        Invoke a Bedrock model with streaming and token tracking.
        
        Note: Token counts are extracted after streaming completes.
        """
        start_time = time.time()
        
        response = self._bedrock.invoke_model_with_response_stream(
            modelId=modelId,
            body=body,
            **kwargs,
        )
        
        # Wrap the stream to track tokens
        return _StreamingResponseWrapper(
            response=response,
            model_id=modelId,
            client=self._client,
            start_time=start_time,
        )
    
    def _extract_tokens(
        self,
        model_id: str,
        response_body: dict[str, Any],
        response: dict[str, Any],
    ) -> tuple[int, int]:
        """Extract token counts from response based on model family."""
        # Anthropic Claude models
        if "anthropic" in model_id.lower():
            usage = response_body.get("usage", {})
            return (
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
            )
        
        # Amazon Titan models
        if "amazon.titan" in model_id.lower():
            return (
                response_body.get("inputTextTokenCount", 0),
                response_body.get("results", [{}])[0].get("tokenCount", 0),
            )
        
        # Meta Llama models
        if "meta.llama" in model_id.lower():
            return (
                response_body.get("prompt_token_count", 0),
                response_body.get("generation_token_count", 0),
            )
        
        # Cohere models
        if "cohere" in model_id.lower():
            meta = response_body.get("meta", {}).get("billed_units", {})
            return (
                meta.get("input_tokens", 0),
                meta.get("output_tokens", 0),
            )
        
        # Mistral models
        if "mistral" in model_id.lower():
            usage = response_body.get("usage", {})
            return (
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
            )
        
        # AI21 models
        if "ai21" in model_id.lower():
            usage = response_body.get("usage", {})
            return (
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
            )
        
        # Default fallback
        return (0, 0)
    
    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the underlying Bedrock client."""
        return getattr(self._bedrock, name)


class _StreamingResponseWrapper:
    """Wrapper for streaming responses to track tokens after completion."""
    
    def __init__(
        self,
        response: Any,
        model_id: str,
        client: TokenTrackrClient,
        start_time: float,
    ):
        self._response = response
        self._model_id = model_id
        self._client = client
        self._start_time = start_time
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._chunks: list[dict] = []
    
    def __iter__(self):
        return self
    
    def __next__(self):
        try:
            event = next(self._response["body"])
            
            if "chunk" in event:
                chunk_data = json.loads(event["chunk"]["bytes"])
                self._chunks.append(chunk_data)
                
                # Extract final token counts from message_stop event
                if chunk_data.get("type") == "message_stop":
                    usage = chunk_data.get("amazon-bedrock-invocationMetrics", {})
                    self._prompt_tokens = usage.get("inputTokenCount", 0)
                    self._completion_tokens = usage.get("outputTokenCount", 0)
                
                return chunk_data
            
            return event
            
        except StopIteration:
            # Record usage when stream ends
            latency_ms = int((time.time() - self._start_time) * 1000)
            self._client.record(
                provider="bedrock",
                model=self._model_id,
                prompt_tokens=self._prompt_tokens,
                completion_tokens=self._completion_tokens,
                latency_ms=latency_ms,
            )
            raise

