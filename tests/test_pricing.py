"""
Pricing Engine Tests
====================
Tests for the token cost calculation engine.
"""

from decimal import Decimal

import pytest

from backend.core.pricing import PricingEngine


class TestPricingEngine:
    """Tests for the pricing engine."""

    @pytest.fixture
    def engine(self) -> PricingEngine:
        """Create a pricing engine with default config."""
        return PricingEngine()

    def test_bedrock_cost_calculation(self, engine: PricingEngine):
        """Test cost calculation for Bedrock models."""
        cost = engine.bedrock_cost(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert isinstance(cost, Decimal)
        assert cost > 0

    def test_azure_openai_cost_calculation(self, engine: PricingEngine):
        """Test cost calculation for Azure OpenAI models."""
        cost = engine.azure_openai_cost(
            model="gpt-4o",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert isinstance(cost, Decimal)
        assert cost > 0

    def test_gemini_cost_calculation(self, engine: PricingEngine):
        """Test cost calculation for Gemini models."""
        cost = engine.gemini_cost(
            model="gemini-1.5-pro",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert isinstance(cost, Decimal)
        assert cost > 0

    def test_unknown_model_uses_defaults(self, engine: PricingEngine):
        """Test that unknown models use default pricing."""
        cost = engine.calculate_cost(
            provider="bedrock",
            model="unknown-model-xyz",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert isinstance(cost, Decimal)
        assert cost > 0

    def test_zero_tokens_zero_cost(self, engine: PricingEngine):
        """Test that zero tokens result in zero cost."""
        cost = engine.calculate_cost(
            provider="bedrock",
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            prompt_tokens=0,
            completion_tokens=0,
        )

        assert cost == Decimal("0")

    def test_get_model_pricing(self, engine: PricingEngine):
        """Test getting pricing for a specific model."""
        input_price, output_price = engine.get_model_pricing(
            provider="azure_openai",
            model="gpt-4o",
        )

        assert isinstance(input_price, Decimal)
        assert isinstance(output_price, Decimal)
        assert input_price > 0
        assert output_price > 0

    def test_provider_normalization(self, engine: PricingEngine):
        """Test that provider names are normalized."""
        # These should all work
        cost1 = engine.calculate_cost("bedrock", "test", 100, 50)
        cost2 = engine.calculate_cost("aws_bedrock", "test", 100, 50)

        # Both should return valid costs
        assert cost1 > 0
        assert cost2 > 0

    def test_get_provider_models(self, engine: PricingEngine):
        """Test getting all models for a provider."""
        models = engine.get_provider_models("bedrock")

        assert isinstance(models, list)
        # Should have some models
        if models:
            model = models[0]
            assert "model" in model
            assert "input_price_per_1k" in model
            assert "output_price_per_1k" in model
