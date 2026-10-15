from app.models import TrainService


class FakeSource:
    """PredictionSource returning canned trains, or raising if given an exception."""

    name = "Fake"

    def __init__(self, result: list[TrainService] | Exception) -> None:
        self.result = result

    async def fetch(self) -> list[TrainService]:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result
