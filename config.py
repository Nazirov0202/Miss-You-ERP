from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str

    # Railway avtomatik beradi (yoki qo'lda .env da)
    DATABASE_URL: str = ""
    REDIS_URL: str = ""

    # Qo'lda sozlash uchun (Railway bo'lmasa)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "telegram_erp"
    DB_USER: str = "erp_user"
    DB_PASS: str = ""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Admin
    ADMIN_TELEGRAM_ID: int = 0

    @property
    def database_url(self) -> str:
        """Railway DATABASE_URL yoki qo'lda sozlash."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Railway postgresql:// beradi, biz asyncpg uchun +asyncpg kerak
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        """Alembic uchun sync URL."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            url = url.replace("postgresql+asyncpg://", "postgresql://")
            return url
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def redis_url(self) -> str:
        """Railway REDIS_URL yoki qo'lda sozlash."""
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
