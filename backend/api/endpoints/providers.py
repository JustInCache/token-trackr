"""
Provider Endpoints
==================
API endpoints for provider information and pricing.
"""

import structlog
from fastapi import APIRouter, HTTPException, status

from backend.core.pricing import get_pricing_engine
from backend.schemas.usage import ModelPricing, ProviderModelsResponse

router = APIRouter()
logger = structlog.get_logger()

VALID_PROVIDERS = {"bedrock", "azure_openai", "gemini"}


@router.get(
    "/{provider}/models",
    response_model=ProviderModelsResponse,
    summary="Get provider models",
    description="Get available models and pricing for a provider",
)
async def get_provider_models(provider: str) -> ProviderModelsResponse:
    """
    Get available models and their pricing for a provider.

    Supported providers:
    - bedrock (AWS Bedrock)
    - azure_openai (Azure OpenAI)
    - gemini (Google Gemini)
    """
    if provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}",
        )

    try:
        pricing_engine = get_pricing_engine()
        models = pricing_engine.get_provider_models(provider)

        return ProviderModelsResponse(
            provider=provider,
            models=[
                ModelPricing(
                    model=m["model"],
                    input_price_per_1k=m["input_price_per_1k"],
                    output_price_per_1k=m["output_price_per_1k"],
                )
                for m in models
            ],
        )
    except Exception as e:
        logger.error("Failed to get provider models", provider=provider, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve provider models",
        ) from e


@router.post(
    "/pricing/reload",
    summary="Reload pricing configuration",
    description="Reload pricing configuration from the YAML file",
)
async def reload_pricing() -> dict[str, str]:
    """
    Reload pricing configuration from the YAML file.

    Useful for updating pricing without restarting the service.
    """
    try:
        pricing_engine = get_pricing_engine()
        pricing_engine.reload()
        return {"status": "ok", "message": "Pricing configuration reloaded"}
    except Exception as e:
        logger.error("Failed to reload pricing", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reload pricing configuration",
        ) from e
