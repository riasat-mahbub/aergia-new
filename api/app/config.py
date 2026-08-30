from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Aergia CV Builder"
    app_version: str = "0.1.0"
    database_url: str = "sqlite+aiosqlite:///data/aergia.db"
    frontend_url: str = "http://localhost:8000"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    uploads_path: str = "./uploads"
    environment: str = "development"
    parser_backend: str = "pdfplumber"
    allow_bearer_tokens: bool = False
    expose_tokens_in_response: bool = False
    csrf_protection_enabled: bool = True

    model_config = {"env_file": ".env", "extra": "allow"}

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> str:
        normalized = str(value).strip().lower()
        allowed: set[str] = {"development", "test", "production"}
        if normalized not in allowed:
            raise ValueError(f"environment must be one of {sorted(allowed)}")
        return normalized


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        env = _settings.environment
        if env == "production" and _settings.secret_key == "change-me-in-production":
            raise RuntimeError(
                "SECRET_KEY is set to the default value 'change-me-in-production'. "
                "Generate a strong random key and set it in .env before running in production."
            )
        if env == "production" and (_settings.allow_bearer_tokens or _settings.expose_tokens_in_response):
            raise RuntimeError(
                "ALLOW_BEARER_TOKENS and EXPOSE_TOKENS_IN_RESPONSE must both be false in production."
            )
    return _settings
