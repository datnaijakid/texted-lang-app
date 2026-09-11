from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Core
    app_name: str = "Texted - Language Learning API"
    environment: str = "development"  # development | production

    # Database. Defaults to local SQLite so the app runs with zero setup.
    # For production, set DATABASE_URL to a Postgres/Neon connection string
    database_url: str = "sqlite:///./texted.db"

    # Auth & Sessions
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours (1 day)

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Cookie security
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # LLM (provider-agnostic conversation engine)
    llm_provider: str = "mock"  # "anthropic" | "openai" | "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # EmailJS (Server-side email delivery)
    emailjs_service_id: str = ""
    emailjs_template_id: str = ""
    emailjs_public_key: str = ""
    emailjs_private_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""
    stripe_success_url: str = "http://localhost:5173?session_id={CHECKOUT_SESSION_ID}&upgraded=true"
    stripe_cancel_url: str = "http://localhost:5173"

    # Grading
    fuzzy_match_threshold: int = 80  # 0-100, rapidfuzz similarity score

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
