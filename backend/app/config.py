"""App settings, loaded from environment variables / the repo-root `.env` file."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
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
    # The one bridge whose chainage the (single) countdown per direction uses.
    # The other bridges are only drawn on the map.
    timing_bridge_id: str = "west-ave"
    # TfL asks clients not to poll faster than this; their responses are cached ~30 s.
    poll_interval_s: int = Field(default=30, ge=20)

    @model_validator(mode="after")
    def _timing_bridge_exists(self) -> "Settings":
        if self.bridges and self.timing_bridge_id not in {b.id for b in self.bridges}:
            raise ValueError(
                f"TIMING_BRIDGE_ID {self.timing_bridge_id!r} not in BRIDGES"
            )
        return self

    @property
    def timing_bridge(self) -> Bridge:
        return next(b for b in self.bridges if b.id == self.timing_bridge_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
