"""Application configuration.

Everything the app needs to know about its environment lives here, loaded once
from environment variables / .env and reused via a cached accessor.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Absolute path to the `backend/` folder, computed from this file's location.
# Used so the app works no matter which directory uvicorn is launched from.
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed settings object. Takes environment variables, returns validated config."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated env vars (Render injects several of its own)
    )

    app_name: str = "AI Resume Analyzer"
    environment: str = "development"
    api_prefix: str = "/api"

    # Browsers block cross-origin calls unless the server explicitly allows them.
    # NoDecode stops pydantic-settings from trying to JSON-parse the env value,
    # so a plain "a,b" string reaches our own validator below.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # 5 MB: comfortably above any real resume, low enough that a malicious
    # 500 MB upload can't exhaust the dyno's disk.
    max_upload_mb: int = 5
    allowed_extensions: Annotated[list[str], NoDecode] = [".pdf", ".docx"]

    temp_dir: Path = Path("data/temp")
    data_dir: Path = Path("data")

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Set false to start without the embedding model. Scores are then computed
    # from the two remaining tiers, renormalised to 0-100. Used by the test
    # suite so CI never downloads 90MB, and as an escape hatch if a host runs
    # out of memory.
    enable_semantic: bool = True

    @field_validator("cors_origins", "allowed_extensions", mode="before")
    @classmethod
    def _split_csv(cls, value: str | list[str]) -> list[str]:
        """Accept either a real list or a comma-separated env string like 'a,b'."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def max_upload_bytes(self) -> int:
        """Upload ceiling in bytes, so the route can compare against len(file)."""
        return self.max_upload_mb * 1024 * 1024

    @property
    def temp_path(self) -> Path:
        """Absolute temp-upload directory, created on first access."""
        path = self.temp_dir if self.temp_dir.is_absolute() else BASE_DIR / self.temp_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_path(self) -> Path:
        """Absolute path to the CSV data directory."""
        return self.data_dir if self.data_dir.is_absolute() else BASE_DIR / self.data_dir


@lru_cache
def get_settings() -> Settings:
    """Return the one shared Settings instance. Cached so the .env is parsed once."""
    return Settings()
