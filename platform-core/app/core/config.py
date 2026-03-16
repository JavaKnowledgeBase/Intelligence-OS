import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Typed app settings for the API name, prefix, and frontend CORS access."""

    app_name: str = os.getenv("APP_NAME", "Torilaure Intelligence OS")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5174"])
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-this-local-dev-secret-before-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_seconds: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", str(60 * 15)))
    refresh_token_expire_seconds: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_SECONDS", str(60 * 60 * 24 * 7)))
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://torilaure:torilaure@localhost:5432/torilaure_security",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    bootstrap_sample_data: bool = os.getenv("BOOTSTRAP_SAMPLE_DATA", "false").lower() == "true"
    bootstrap_auth_users: bool = os.getenv("BOOTSTRAP_AUTH_USERS", "true").lower() == "true"


# Singleton settings object used across the backend.
settings = Settings()
