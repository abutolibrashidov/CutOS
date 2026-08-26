from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Barber Platform"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "barber"
    POSTGRES_PASSWORD: str = "barber"
    POSTGRES_DB: str = "barber_db"

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL(self) -> str:
        return URL.create(
                "postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.POSTGRES_DB,
            ).render_as_string(hide_password=False)

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync URL used by Alembic migrations."""
        return URL.create(
                "postgresql+psycopg2",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.POSTGRES_DB,
            ).render_as_string(hide_password=False)

    # Tests always use a separately named database.  It is deliberately not
    # derived from POSTGRES_DB so test setup cannot target the development DB.
    TEST_POSTGRES_DB: str = "barber_test_db"

    @computed_field  # type: ignore[misc]
    @property
    def TEST_DATABASE_URL(self) -> str:
        return URL.create(
                "postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.TEST_POSTGRES_DB,
            ).render_as_string(hide_password=False)

    # ── Telegram ─────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    MINI_APP_URL: str = ""  # your current tunnel URL, e.g. https://xxx.trycloudflare.com
    TELEGRAM_INIT_DATA_MAX_AGE_SECONDS: int = Field(default=3600, gt=0)
    TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS: int = Field(default=30, ge=0)

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Timezone ─────────────────────────────────────────────────────────────
    # All timestamps stored in UTC. APP_TIMEZONE is used by frontend/display
    # logic only, not for DB storage.
    APP_TIMEZONE: str = "Asia/Tashkent"


@lru_cache
def get_settings() -> Settings:
    return Settings()
