"""Response models for the health endpoint."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Takes nothing; returned by GET /api/health to prove the service is alive."""

    status: str = Field(examples=["ok"])
    app: str
    environment: str
    version: str
    # True once the embedding model is loaded at startup (wired in Phase 5).
    embeddings_ready: bool
