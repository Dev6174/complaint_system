# pyrefly: ignore [missing-import]
import os
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Fix 2 — Secret key guard
# The default value "super-secret-dev-key-change-in-production" is committed
# in the repo. If the app starts in a non-dev environment with that value
# still set, it is a critical vulnerability. We detect it at startup and
# refuse to run rather than silently accepting the insecure default.
# ---------------------------------------------------------------------------
_INSECURE_DEFAULTS = {
    "super-secret-dev-key-change-in-production",
    "changeme",
    "secret",
    "",
}

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./complaint_system.db"
    REDIS_URL: str = ""
    SECRET_KEY: str = "super-secret-dev-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Comma-separated list of allowed CORS origins.
    # Example: "https://myapp.example.com,https://staging.example.com"
    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    # AI classification service
    AI_CLASSIFIER_ENDPOINT: str = "https://api.external-categorization.local/classify"
    AI_CLASSIFIER_API_KEY: str = ""

    # Community verification escalation
    VERIFICATION_THRESHOLD: int = 5

    # Rate limiting
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 60
    RATE_LIMIT_LOGIN_MAX: int = 5
    RATE_LIMIT_ISSUE_MAX: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_secrets(self) -> None:
        """
        Call once at startup. Exits the process if SECRET_KEY is an insecure
        default AND the environment is not explicitly flagged as development.
        Set APP_ENV=development in your .env to suppress this check locally.
        """
        app_env = os.getenv("APP_ENV", "production").lower()
        if app_env == "development":
            return

        if self.SECRET_KEY.strip() in _INSECURE_DEFAULTS:
            print(
                "[FATAL] SECRET_KEY is set to an insecure default value. "
                "Generate a strong key with:\n"
                "    python -c \"import secrets; print(secrets.token_hex(32))\"\n"
                "and set it in your .env file. "
                "To suppress this check in local dev, set APP_ENV=development.",
                file=sys.stderr,
            )
            sys.exit(1)


settings = Settings()
settings.validate_secrets()
