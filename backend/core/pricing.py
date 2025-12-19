"""
Token Cost Engine
=================
Multi-cloud pricing calculations for AWS Bedrock, Azure OpenAI, and Google Gemini.
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
import structlog

from backend.config import settings

logger = structlog.get_logger()


class PricingEngine:
    """
    Token pricing engine supporting multiple LLM providers.
    
    Loads pricing from YAML configuration with optional tenant overrides.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or settings.pricing_config_path
        self._pricing_data: dict[str, Any] = {}
        self._load_pricing()

    def _load_pricing(self) -> None:
        """Load pricing configuration from YAML file."""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            logger.warning("Pricing config not found, using defaults", path=self.config_path)
            self._pricing_data = self._get_default_pricing()
            return

        try:
            with open(config_file) as f:
                self._pricing_data = yaml.safe_load(f)
            logger.info("Loaded pricing configuration", path=self.config_path)
        except Exception as e:
            logger.error("Failed to load pricing config", error=str(e))
            self._pricing_data = self._get_default_pricing()

    def _get_default_pricing(self) -> dict[str, Any]:
        """Return default pricing if config file is missing."""
        return {
            "defaults": {
                "bedrock": {"input_per_1k": 0.002, "output_per_1k": 0.006},
                "azure_openai": {"input_per_1k": 0.002, "output_per_1k": 0.006},
                "gemini": {"input_per_1k": 0.001, "output_per_1k": 0.003},
            }
        }

    def reload(self) -> None:
        """Reload pricing configuration from file."""
        self._load_pricing()

    def get_model_pricing(
        self,
        provider: str,
        model: str,
    ) -> tuple[Decimal, Decimal]:
        """
        Get input and output pricing per 1K tokens for a model.
        
        Returns:
            Tuple of (input_price_per_1k, output_price_per_1k)
        """
        # Map provider names to config keys
        provider_key = self._normalize_provider(provider)
        
        # Try to find exact model match
        provider_pricing = self._pricing_data.get(provider_key, {})
        
        if model in provider_pricing:
            pricing = provider_pricing[model]
            return (
                Decimal(str(pricing.get("input_per_1k", 0))),
                Decimal(str(pricing.get("output_per_1k", 0))),
            )
        
        # Try partial match (model name might be truncated)
        for model_key, pricing in provider_pricing.items():
            if model.startswith(model_key) or model_key.startswith(model):
                return (
                    Decimal(str(pricing.get("input_per_1k", 0))),
                    Decimal(str(pricing.get("output_per_1k", 0))),
                )
        
        # Fall back to defaults
        defaults = self._pricing_data.get("defaults", {}).get(provider_key, {})
        return (
            Decimal(str(defaults.get("input_per_1k", 0.002))),
            Decimal(str(defaults.get("output_per_1k", 0.006))),
        )

    def _normalize_provider(self, provider: str) -> str:
        """Normalize provider name to config key."""
        mapping = {
            "bedrock": "bedrock",
            "aws_bedrock": "bedrock",
            "azure_openai": "azure_openai",
            "azure": "azure_openai",
            "gemini": "gemini",
            "google": "gemini",
            "google_gemini": "gemini",
        }
        return mapping.get(provider.lower(), provider.lower())

    def calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        tenant_id: Optional[str] = None,
    ) -> Decimal:
        """
        Calculate total cost for a token usage event.
        
        Args:
            provider: LLM provider (bedrock, azure_openai, gemini)
            model: Model identifier
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            tenant_id: Optional tenant ID for custom pricing
            
        Returns:
            Calculated cost in USD
        """
        input_price, output_price = self.get_model_pricing(provider, model)
        
        # Apply tenant discount if configured
        discount = self._get_tenant_discount(tenant_id) if tenant_id else Decimal("0")
        
        # Calculate raw cost
        input_cost = (Decimal(prompt_tokens) / Decimal("1000")) * input_price
        output_cost = (Decimal(completion_tokens) / Decimal("1000")) * output_price
        total_cost = input_cost + output_cost
        
        # Apply discount
        if discount > 0:
            total_cost = total_cost * (Decimal("1") - discount / Decimal("100"))
        
        return total_cost.quantize(Decimal("0.0000000001"))

    def _get_tenant_discount(self, tenant_id: str) -> Decimal:
        """Get discount percentage for a tenant."""
        overrides = self._pricing_data.get("tenant_overrides", {})
        tenant_config = overrides.get(tenant_id, {})
        return Decimal(str(tenant_config.get("discount_percent", 0)))

    def bedrock_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Decimal:
        """Calculate cost for AWS Bedrock usage."""
        return self.calculate_cost("bedrock", model, prompt_tokens, completion_tokens)

    def azure_openai_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Decimal:
        """Calculate cost for Azure OpenAI usage."""
        return self.calculate_cost("azure_openai", model, prompt_tokens, completion_tokens)

    def gemini_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Decimal:
        """Calculate cost for Google Gemini usage."""
        return self.calculate_cost("gemini", model, prompt_tokens, completion_tokens)

    def get_provider_models(self, provider: str) -> list[dict[str, Any]]:
        """Get all available models and their pricing for a provider."""
        provider_key = self._normalize_provider(provider)
        provider_pricing = self._pricing_data.get(provider_key, {})
        
        models = []
        for model, pricing in provider_pricing.items():
            if isinstance(pricing, dict) and "input_per_1k" in pricing:
                models.append({
                    "model": model,
                    "input_price_per_1k": Decimal(str(pricing["input_per_1k"])),
                    "output_price_per_1k": Decimal(str(pricing["output_per_1k"])),
                })
        
        return sorted(models, key=lambda x: x["model"])


@lru_cache
def get_pricing_engine() -> PricingEngine:
    """Get cached pricing engine instance."""
    return PricingEngine()

