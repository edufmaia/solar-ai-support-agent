from functools import lru_cache
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    app_env: str = "development"
    app_name: str = "solar-ai-support-agent"
    app_port: int = 8000

    database_host: str = "postgres"
    database_port: int = 5432
    database_name: str = "solar_ai_support"
    database_user: str = "solar"
    database_password: str = "solar_password"
    database_url: str | None = None

    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_input_price_per_1m_tokens: Decimal = Decimal("0.15")
    openai_output_price_per_1m_tokens: Decimal = Decimal("0.60")

    anthropic_api_key: str | None = None
    claude_model: str = "claude-opus-4-8"
    claude_max_tokens: int = 1024
    claude_input_price_per_1m_tokens: Decimal = Decimal("5.00")
    claude_output_price_per_1m_tokens: Decimal = Decimal("25.00")

    geocoding_provider: str = "mock"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org/search"
    nominatim_user_agent: str = "solar-ai-support-agent"
    geocoding_timeout_seconds: float = 5.0

    solar_provider: str = "mock"

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_url: str | None = None
    session_ttl_seconds: int = 3600

    chatwoot_base_url: str | None = None
    chatwoot_api_access_token: str | None = None
    chatwoot_timeout_seconds: float = 5.0
    chatwoot_conversation_ttl_seconds: int = 604800

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    def get_redis_url(self) -> str:
        if self.redis_url:
            return self.redis_url

        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
