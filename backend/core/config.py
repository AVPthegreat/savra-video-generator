"""Environment-driven settings — add DATABASE_URL for DB connection."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.core.secrets import get_secret

logger = logging.getLogger(__name__)

_INSECURE_DEFAULTS = {"change_me", "", "admin123", "replace_with_strong_password", "replace_with_long_random_secret"}


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    gcp_project_id: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    svg_assets_dir: str = Field(default="../assets/svgs", alias="SVG_ASSETS_DIR")
    max_input_chars: int = Field(default=15_000, alias="MAX_INPUT_CHARS")
    max_upload_mb: int = Field(default=20, alias="MAX_UPLOAD_MB")
    run_retention_count: int = Field(default=20, alias="RUN_RETENTION_COUNT")
    output_dir: str = Field(default="../renderer/public", alias="OUTPUT_DIR")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    iconify_base_url: str = Field(default="https://api.iconify.design", alias="ICONIFY_BASE_URL")
    auto_create_tables: bool = Field(default=True, alias="AUTO_CREATE_TABLES")
    recover_stale_jobs_on_startup: bool = Field(default=True, alias="RECOVER_STALE_JOBS_ON_STARTUP")
    database_ssl_mode: str = Field(default="prefer", alias="DATABASE_SSL_MODE")
    job_worker_count: int = Field(default=2, alias="JOB_WORKER_COUNT")
    job_queue_capacity: int = Field(default=6, alias="JOB_QUEUE_CAPACITY")
    max_concurrent_renders: int = Field(default=1, alias="MAX_CONCURRENT_RENDERS")
    enable_auth: bool = Field(default=True, alias="ENABLE_AUTH")
    auth_username: str = Field(default="admin", alias="AUTH_USERNAME")
    auth_password: str = Field(default="change_me", validation_alias=AliasChoices("AUTH_PASSWORD", "ADMIN_PASSWORD"))
    jwt_secret: str = Field(default="change_me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES") # 24h
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")

    # ── SEMANTIC ASSET PIPELINE ──────────────────────────────────────────────
    use_multi_model_director: bool = Field(default=False, alias="USE_MULTI_MODEL_DIRECTOR")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    cerebras_api_key: str = Field(default="", alias="CEREBRAS_API_KEY")
    
    asset_index_path: str = Field(default="assets/index.json", alias="ASSET_INDEX_PATH")
    asset_undraw_dir: str = Field(default="assets/undraw", alias="ASSET_UNDRAW_DIR")
    asset_cache_dir: str = Field(default="/tmp/iconify_cache", alias="ASSET_CACHE_DIR")
    semantic_threshold: float = Field(default=0.30, alias="SEMANTIC_THRESHOLD")
    gcs_assets_bucket: str = Field(default="gs://savra-video-assets", alias="GCS_ASSETS_BUCKET")

    # ── PRODUCTION ASSETS ────────────────────────────────────────────────────
    gcs_bucket_name: str | None = Field(default=None, alias="GCS_BUCKET_NAME")

    # ── DATABASE ─────────────────────────────────────────────────────────────
    # SQLite for local dev (no setup needed — file created automatically)
    # Switch to PostgreSQL for production:
    #   DATABASE_URL=postgresql://savra:password@localhost:5432/savradevdb
    database_url: str = Field(
        default="sqlite:///./savra.db",
        alias="DATABASE_URL",
    )

    @model_validator(mode="after")
    def resolve_production_secrets(self) -> "Settings":
        """Fetch secrets from GCP Secret Manager if in production and project ID is set."""

        if self.app_env.lower() == "production" and self.gcp_project_id:
            # Attempt to override sensitive fields from Secret Manager
            db_url = get_secret("DATABASE_URL", self.gcp_project_id)
            if db_url:
                self.database_url = db_url
                logger.info("Loaded DATABASE_URL from Secret Manager")

            gemini_key = get_secret("GEMINI_API_KEY", self.gcp_project_id)
            if gemini_key:
                self.gemini_api_key = gemini_key
                logger.info("Loaded GEMINI_API_KEY from Secret Manager")

            jwt_sec = get_secret("JWT_SECRET", self.gcp_project_id)
            if jwt_sec:
                self.jwt_secret = jwt_sec
                logger.info("Loaded JWT_SECRET from Secret Manager")

            admin_pwd = get_secret("ADMIN_PASSWORD", self.gcp_project_id)
            if admin_pwd:
                self.auth_password = admin_pwd
                logger.info("Loaded ADMIN_PASSWORD from Secret Manager")

        return self

    @model_validator(mode="after")
    def validate_database_url_for_environment(self) -> "Settings":
        """Robust safety checks for Cloud Run deployment."""

        if self.app_env.lower() == "production":
            # Sanitize DATABASE_URL if it contains local-only hostnames
            if "@db:" in self.database_url or "@localhost" in self.database_url:
                if not self.database_url.startswith("sqlite"):
                    logger.warning("DATABASE_URL contains local hostname (@db or @localhost) in production.")

            if self.database_url.startswith("sqlite"):
                if not self.database_url.startswith("sqlite:////tmp/"):
                    logger.warning("Relative SQLite path in production; redirecting to /tmp/savra.db.")
                    self.database_url = "sqlite:////tmp/savra.db"

        return self

    @model_validator(mode="after")
    def enforce_secure_defaults_in_production(self) -> "Settings":
        """Refuse to start in production with insecure default credentials."""

        if self.app_env.lower() != "production":
            return self

        if not self.enable_auth:
            logger.warning(
                "ENABLE_AUTH is disabled in production — authentication is OFF. "
                "This is a security risk unless protected by an external IAM layer."
            )
            return self

        errors: list[str] = []

        if self.auth_password in _INSECURE_DEFAULTS:
            errors.append("AUTH_PASSWORD is set to an insecure default")

        if self.jwt_secret in _INSECURE_DEFAULTS:
            errors.append("JWT_SECRET is set to an insecure default")
        
        if not self.gemini_api_key or self.gemini_api_key in _INSECURE_DEFAULTS:
            errors.append("GEMINI_API_KEY is missing or invalid")

        if errors:
            raise ValueError(
                f"Refusing to start in production with insecure configuration: {'; '.join(errors)}. "
                "Set strong values via environment variables or GCP Secret Manager."
            )

        return self

    model_config = SettingsConfigDict(
        env_file=(".env"),
        extra="ignore",
        populate_by_name=True,
    )

    def resolve_svg_assets_dir(self, base_dir: str | Path) -> Path:
        return _resolve_path(base_dir=base_dir, value=self.svg_assets_dir)

    def resolve_output_dir(self, base_dir: str | Path) -> Path:
        return _resolve_path(base_dir=base_dir, value=self.output_dir)


def _resolve_path(base_dir: str | Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (Path(base_dir) / candidate).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()