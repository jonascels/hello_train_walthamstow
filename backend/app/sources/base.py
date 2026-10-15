from typing import Protocol

from app.models import TrainService


class PredictionSource(Protocol):
    """Anything that can report the trains currently running on our route."""

    name: str  # shown in the UI's attribution, e.g. "TfL"

    async def fetch(self) -> list[TrainService]: ...
