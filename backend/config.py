from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from the abm-script root (two levels up from this file)
_env_file = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- AI ---
    openai_api_key: str = ""
    abm_ai_model: str = "gpt-4.1-nano"

    # --- Identity (Tomba + Apify company enricher) ---
    tomba_api_key: str = ""
    tomba_api_secret: str = ""
    apify_token: str = ""

    # --- Storage / Cache ---
    storage_type: str = Field(default="memory", description="memory | file")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    cache_dir: str = Field(default=".abm-cache", description="Directory for file-based cache")

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8001
    cors_origins: str = Field(default="*", description="Comma-separated allowed origins, or * for all")
    debug: bool = False

    @field_validator("cors_origins")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v.strip()

    def get_cors_origins(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
