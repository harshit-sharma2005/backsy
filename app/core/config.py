"""Application configuration using pydantic-settings.

This module centralizes environment-driven settings like export directory,
file size limits, and cleanup intervals.
"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the API.

    Attributes:
        APP_NAME: Friendly application name.
        EXPORT_DIR: Directory where exported files are written.
        EXPORT_TTL_SECONDS: Time-to-live for exported files before cleanup.
        CLEANUP_INTERVAL_SECONDS: How often the cleanup process runs.
        MAX_UPLOAD_MB: Maximum upload size in megabytes (soft limit, validated in code).
        CORS_ALLOW_ORIGINS: Comma-separated list of allowed origins for CORS.
    """

    model_config = SettingsConfigDict(env_prefix="CSVAPI_", env_file=".env", extra="ignore")

    APP_NAME: str = "CSV Processing API"
    EXPORT_DIR: Path = Path("exports")
    EXPORT_TTL_SECONDS: int = 60 * 60 * 6  # 6 hours
    CLEANUP_INTERVAL_SECONDS: int = 60 * 15  # 15 minutes
    MAX_UPLOAD_MB: int = 50
    CORS_ALLOW_ORIGINS: str = "*"


settings = Settings()
# Ensure export directory exists on import (safe in most contexts)
settings.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
