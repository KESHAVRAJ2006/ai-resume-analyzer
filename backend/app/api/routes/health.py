"""Health-check route. Kept trivial so uptime probes never touch heavy code."""

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health(request: Request) -> HealthResponse:
    """Take no input, return service status, environment and model-readiness flag."""
    settings = get_settings()
    # app.state is populated by the lifespan handler in main.py.
    ml_models = getattr(request.app.state, "ml_models", {})
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
        version=request.app.version,
        embeddings_ready="embeddings" in ml_models,
    )
