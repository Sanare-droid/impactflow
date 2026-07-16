from functools import lru_cache
from typing import List
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Railway/Heroku provide postgres:// or postgresql:// — SQLAlchemy async needs asyncpg."""
    raw = (url or "").strip()
    if not raw:
        return raw
    for prefix in ("postgres://", "postgresql://"):
        if raw.startswith(prefix) and "+asyncpg" not in raw.split("://", 1)[0]:
            return "postgresql+asyncpg://" + raw[len(prefix) :]
    if raw.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + raw[len("postgresql+psycopg2://") :]
    return raw


class Settings(BaseSettings):
    """Central application configuration. All values come from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ImpactFlow AI"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    backend_cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    # Extra browser origins (Netlify deploy previews / production sites)
    backend_cors_origin_regex: str = r"https://.*\.netlify\.app"

    # Optional bootstrap superadmin (created on API startup if both set)
    superadmin_email: str = ""
    superadmin_password: str = ""
    superadmin_first_name: str = "Platform"
    superadmin_last_name: str = "Admin"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "impactflow"
    postgres_password: str = "change_me_strong_password"
    postgres_db: str = "impactflow"
    database_url: str = (
        "postgresql+asyncpg://impactflow:change_me_strong_password@localhost:5432/impactflow"
    )

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change_me_to_a_64_char_random_secret_key_immediately"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    mfa_issuer: str = "ImpactFlow AI"

    encryption_key: str = "generate_a_fernet_key_and_replace_this"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "impactflow"
    s3_secret_key: str = "change_me_minio_secret"
    s3_bucket: str = "impactflow"
    s3_region: str = "us-east-1"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Email — Resend API preferred; SMTP fallback; else log stub
    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # Background jobs
    jobs_poll_seconds: int = 30
    jobs_enabled: bool = True

    # Password policy
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_minutes: int = 15

    @property
    def email_from(self) -> str:
        from_addr = (self.smtp_from or "").strip()
        if from_addr and from_addr.lower() != "resend":
            return from_addr
        # SMTP_USER for Resend is literally "resend" — not a valid From
        return "ImpactFlow <onboarding@resend.dev>"

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                import json

                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def parse_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    @field_validator(
        "superadmin_email",
        "superadmin_password",
        "jwt_secret_key",
        "encryption_key",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def database_host(self) -> str:
        try:
            return urlparse(self.database_url).hostname or ""
        except Exception:
            return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
