from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables or a local `.env` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required (no default), e.g. postgresql+asyncpg://todo:todo@localhost:5432/todoapp
    database_url: str

    jwt_secret_key: str  # required: no default, so a missing key fails at startup
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 20

    @property
    def access_token_expire(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)


# Required fields are filled from the environment / .env at runtime, which type checkers
# can't see, so they report a missing argument.
settings = Settings()  # pyright: ignore[reportCallIssue]
