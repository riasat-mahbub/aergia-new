from ipaddress import ip_network

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
    # GLiNER2.5-small is intentionally fixed as the production model. The
    # revision is configurable only so a pinned artifact can be promoted in a
    # controlled deployment; the extractor rejects other model families.
    gliner2_model_revision: str = "cab1bddfd30fda7b803a4691c41f90378a2d517a"
    gliner2_chunk_size: int = 384
    gliner2_chunk_overlap: int = 64
    allow_bearer_tokens: bool = False
    expose_tokens_in_response: bool = False
    csrf_protection_enabled: bool = True
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""
    turnstile_expected_hostname: str = ""
    turnstile_expected_action: str = "register"
    turnstile_verification_timeout_seconds: float = 3.0
    turnstile_bypass: bool = False
    trusted_proxy_ips: str = ""
    forwarded_allow_ips: str = ""

    model_config = {"env_file": ".env", "extra": "allow"}

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> str:
        normalized = str(value).strip().lower()
        allowed: set[str] = {"development", "test", "production"}
        if normalized not in allowed:
            raise ValueError(f"environment must be one of {sorted(allowed)}")
        return normalized

    @field_validator(
        "turnstile_site_key",
        "turnstile_secret_key",
        "turnstile_expected_hostname",
        "turnstile_expected_action",
        mode="before",
    )
    @classmethod
    def normalize_turnstile_text(cls, value: object) -> str:
        return str(value).strip()

    @field_validator("turnstile_verification_timeout_seconds")
    @classmethod
    def validate_turnstile_timeout(cls, value: float) -> float:
        if not 0.1 <= value <= 10.0:
            raise ValueError("turnstile verification timeout must be between 0.1 and 10 seconds")
        return value

    @field_validator("trusted_proxy_ips")
    @classmethod
    def normalize_trusted_proxy_ips(cls, value: str) -> str:
        networks: list[str] = []
        for item in value.split(","):
            candidate = item.strip()
            if not candidate:
                continue
            try:
                networks.append(str(ip_network(candidate, strict=False)))
            except ValueError as exc:
                raise ValueError(f"invalid trusted proxy network: {candidate}") from exc
        return ",".join(networks)

    @field_validator("forwarded_allow_ips")
    @classmethod
    def validate_forwarded_allow_ips(cls, value: str) -> str:
        peers = [item.strip() for item in value.split(",") if item.strip()]
        if "*" in peers:
            raise ValueError("FORWARDED_ALLOW_IPS must contain known proxy addresses, not '*'")
        return ",".join(peers)

    @property
    def turnstile_configured(self) -> bool:
        return bool(
            self.turnstile_site_key
            and self.turnstile_secret_key
            and self.turnstile_expected_hostname
            and self.turnstile_expected_action
        )

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
        if _settings.turnstile_bypass and env not in {"development", "test"}:
            raise RuntimeError("TURNSTILE_BYPASS is only permitted in development or test environments.")
        if env == "production" and not _settings.turnstile_configured:
            raise RuntimeError(
                "TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY, TURNSTILE_EXPECTED_HOSTNAME, and "
                "TURNSTILE_EXPECTED_ACTION must be configured in production."
            )
    return _settings
