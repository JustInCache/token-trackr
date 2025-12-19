"""
Token Trackr SDK
==================
Python SDK for tracking LLM token consumption across
AWS Bedrock, Azure OpenAI, and Google Gemini.
"""

from token_trackr.client import TokenTrackrClient
from token_trackr.config import TokenTrackrConfig
from token_trackr.metadata import get_host_metadata
from token_trackr.wrappers import (
    BedrockWrapper,
    AzureOpenAIWrapper,
    GeminiWrapper,
)

__version__ = "1.0.0"

__all__ = [
    "TokenTrackrClient",
    "TokenTrackrConfig",
    "BedrockWrapper",
    "AzureOpenAIWrapper",
    "GeminiWrapper",
    "get_host_metadata",
]

