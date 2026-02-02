from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Aergia CV Builder"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://aergia_user:aergia_pass@localhost:5432/aergia"
    frontend_url: str = "http://localhost:8000"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    uploads_path: str = "/app/uploads"

    model_config = {"env_file": ".env", "extra": "allow"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
