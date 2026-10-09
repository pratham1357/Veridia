"""Application configuration, loaded from environment variables (prefix ``VERIDIA_``)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERIDIA_", env_file=".env", extra="ignore")

    app_name: str = "VERIDIA"
    version: str = "0.5.0"
    cors_origins: list[str] = ["http://localhost:5173"]

    max_upload_bytes: int = 10 * 1024 * 1024
    max_pixels: int = 8_000_000  # bounds memory use of pixel-domain analysis

    persist: bool = True  # False: keep everything in memory (lost on restart)
    storage_dir: Path = REPO_ROOT / "storage"


settings = Settings()
