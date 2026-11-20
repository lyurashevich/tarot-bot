from functools import lru_cache

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


class DeckImportSettings(BotSettings):
    """Settings for scripts/import_deck.py."""

    # Private channel where the bot posts card images to get their Telegram file_ids.
    storage_chat_id: int


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


@lru_cache
def get_bot_settings() -> BotSettings:
    return BotSettings()
