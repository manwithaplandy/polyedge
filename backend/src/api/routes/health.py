"""Health check endpoints."""

from fastapi import APIRouter

from src.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "polyedge-api"}


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service status."""
    settings = get_settings()

    return {
        "status": "healthy",
        "service": "polyedge-api",
        "environment": settings.environment,
        "use_mock_data": settings.use_mock_data,
        "services": {
            "supabase": "configured" if settings.supabase_url else "not_configured",
            "newsapi": "configured" if settings.newsapi_key else "not_configured",
            "twitter": "configured" if settings.twitter_bearer_token else "not_configured",
        },
    }
