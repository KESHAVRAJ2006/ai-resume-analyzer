"""FastAPI application factory, lifespan and global error handling.

FAIRNESS NOTE (applies to the whole codebase): this system never extracts,
stores or scores name, gender, age, photo, religion, nationality, marital
status or disability. Only skills and role-relevant text are analysed, and the
resulting score is an estimate of skill overlap - not a hiring decision.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import analyze, health, report, roles
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("app")

API_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run once on startup and once on shutdown.

    Anything expensive (the sentence-transformers model, precomputed role
    embeddings) is loaded here into app.state so it is built ONCE per process
    rather than once per request. Phase 5 fills this dict; Phase 1 only proves
    the hook works.
    """
    settings = get_settings()
    ml_models: dict[str, Any] = {}
    app.state.ml_models = ml_models
    settings.temp_path  # touch the property so the temp dir exists before uploads

    if settings.enable_semantic:
        # Imported here so a run with ENABLE_SEMANTIC=false never pays torch's
        # import cost, which is most of the startup time.
        from app.core.embeddings import build_embedding_index

        try:
            ml_models["embeddings"] = build_embedding_index(settings.embedding_model)
        except Exception:
            # A failed download must not take the API down: the scorer falls
            # back to the two-tier formula and /api/health reports it.
            logger.exception("Embedding model failed to load; continuing without it")
    else:
        logger.info("Semantic tier disabled by configuration")

    logger.info(
        "Startup complete | env=%s | semantic=%s",
        settings.environment,
        "embeddings" in ml_models,
    )
    yield
    app.state.ml_models.clear()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Take no input, return a fully configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=API_VERSION,
        description="Resume skill extraction, role matching and gap analysis.",
        lifespan=lifespan,
        docs_url="/docs",
    )

    # The React dev server and the deployed frontend live on different origins,
    # so the browser needs an explicit allow-list from us.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # we use no cookies; keeps the allow-list strict
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Convert any uncaught error into clean JSON instead of an HTML traceback."""
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again."},
        )

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(roles.router, prefix=settings.api_prefix)
    app.include_router(analyze.router, prefix=settings.api_prefix)
    app.include_router(report.router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """Friendly landing payload so hitting the bare URL is not a 404."""
        return {"service": settings.app_name, "docs": "/docs", "health": "/api/health"}

    return app


app = create_app()
