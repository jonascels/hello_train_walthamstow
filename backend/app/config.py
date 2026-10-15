"""App settings, loaded from environment variables / the repo-root `.env` file."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Bridge(BaseModel):
    """A point on the line where we time passing trains."""

    id: str
    name: str
    lat: float
    lon: float


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    tfl_app_key: str = ""
    line_id: str = "weaver"
    # JSON list in .env, e.g. BRIDGES='[{"id": "west-ave", "name": "West Ave", "lat": 51.58, "lon": -0.01}]'
    bridges: list[Bridge] = []
    poll_interval_s: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
