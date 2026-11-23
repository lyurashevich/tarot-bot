from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV = SettingsConfigDict(env_file=".env", extra="ignore")


class DatabaseSettings(BaseSettings):
    """Database connection settings. Kept separate so migrations run without a bot token."""

    model_config = _ENV

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "tarot_bot"
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("postgres")

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password.get_secret_value()}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


class BotSettings(BaseSettings):
    """Settings the running bot needs on top of the database ones."""

    model_config = _ENV

    bot_token: SecretStr
    log_level: str = "INFO"
    # "Today" for the card of the day is the date in this time zone.
    bot_timezone: str = "Europe/Minsk"
    # The deck whose images users see (code from scripts/import_deck.py --deck).
    default_deck_code: str = "rider_waite"

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.bot_timezone)


class DeckImportSettings(BotSettings):
    """Settings for scripts/import_deck.py."""

    # Private channel where the bot posts card images to get their Telegram file_ids.
    storage_chat_id: int


class AISettings(BaseSettings):
    """AI providers. Providers are tried in AI_PROVIDERS order; one without a key is skipped."""

    model_config = _ENV

    ai_providers: str = "openrouter"

    groq_api_key: SecretStr | None = None
    groq_model: str | None = None
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str | None = None
    mistral_api_key: SecretStr | None = None
    mistral_model: str | None = None

    ai_timeout_seconds: float = 60
    # Upper bound for one answer. Reasoning models spend part of it on hidden thinking.
    ai_max_tokens: int = 4096
    ai_max_concurrency: int = 4
    # How long to skip a provider after "rate limit exceeded" if it does not say itself.
    # Short: on OpenRouter a 429 often means only that one free model is busy right now.
    ai_rate_limit_cooldown_seconds: float = 60
    # Every AI request with prompt and answer, as JSON Lines. Empty: do not write it.
    ai_request_log_path: str = "logs/ai_requests.jsonl"

    @property
    def provider_order(self) -> list[str]:
        return [name.strip().lower() for name in self.ai_providers.split(",") if name.strip()]

    def api_key(self, provider: str) -> str | None:
        key: SecretStr | None = getattr(self, f"{provider}_api_key", None)
        return key.get_secret_value() if key else None

    def models(self, provider: str) -> list[str]:
        """<PROVIDER>_MODEL, which may list several models separated by commas."""
        value: str | None = getattr(self, f"{provider}_model", None)
        return [model.strip() for model in (value or "").split(",") if model.strip()]


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


@lru_cache
def get_bot_settings() -> BotSettings:
    return BotSettings()
