"""Background loop: fetch predictions every `poll_interval_s` and keep the latest.

Milestone 3 only logs the normalised trains; ETA calculation and pushing to
clients come in milestones 4 and 5.
"""

import asyncio
import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.models import TrainService
from app.services.geometry import Geometry
from app.sources.base import PredictionSource

log = logging.getLogger(__name__)
LONDON = ZoneInfo("Europe/London")  # display only; everything else stays UTC


class Poller:
    def __init__(
        self, source: PredictionSource, geometry: Geometry, interval_s: int
    ) -> None:
        self.source = source
        self.geometry = geometry
        self.interval_s = interval_s
        self.trains: list[TrainService] = []
        self.last_success: datetime | None = None
        self.last_error: str | None = None

    async def poll_once(self) -> None:
        try:
            self.trains = await self.source.fetch()
        except Exception as exc:  # noqa: BLE001 — never let one bad poll stop the loop
            self.last_error = repr(exc)
            log.warning("%s fetch failed: %r", self.source.name, exc)
            return
        self.last_success = datetime.now(UTC)
        self.last_error = None
        self._log_trains()

    async def run(self) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(self.interval_s)

    def _log_trains(self) -> None:
        """Log trains still due at a station either side of the timing bridge.

        Some of these may already be past the bridge; working that out is
        the ETA service's job (milestone 4).
        """
        bridge = self.geometry.timing_bridge
        before, after = self.geometry.stations_either_side(bridge.chainage_m)
        bracket = {before.id, after.id}
        names = {s.id: s.name for s in self.geometry.stations}

        nearby = [t for t in self.trains if bracket & {c.station_id for c in t.calls}]
        log.info(
            "%s: %d trains on route, %d due at %s or %s",
            self.source.name,
            len(self.trains),
            len(nearby),
            before.name,
            after.name,
        )
        for t in nearby:
            calls = ", ".join(
                f"{names[c.station_id]} {c.arr.astimezone(LONDON):%H:%M}"
                for c in t.calls
                if c.arr
            )
            log.info("  %-4s → %-24s %s: %s", t.direction, t.destination, t.id, calls)
