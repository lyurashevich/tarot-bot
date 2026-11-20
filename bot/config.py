from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bot settings, read from environment variables and the .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: SecretStr

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "tarot_bot"
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("postgres")

    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password.get_secret_value()}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
