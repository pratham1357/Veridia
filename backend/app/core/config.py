"""Application configuration, loaded from environment variables (prefix ``VERIDIA_``)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERIDIA_", env_file=".env", extra="ignore")

    app_name: str = "VERIDIA"
    version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
