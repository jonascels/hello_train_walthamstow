"""Background loop: fetch predictions every `poll_interval_s`, compute bridge
ETAs and keep the latest snapshot."""

import asyncio
import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.models import BridgeSnapshot, LiveUpdate
from app.services.eta import EtaTracker
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
        self.tracker = EtaTracker(geometry)
        self.snapshot: BridgeSnapshot | None = None
        self.last_success: datetime | None = None
        self.last_error: str | None = None
        # One queue per connected WebSocket client.
        self._subscribers: set[asyncio.Queue[LiveUpdate]] = set()

    def live_update(self) -> LiveUpdate:
        return LiveUpdate(
            server_time=datetime.now(UTC),
            source=self.source.name,
            snapshot=self.snapshot,
            last_success=self.last_success,
            last_error=self.last_error,
        )

    def subscribe(self) -> asyncio.Queue[LiveUpdate]:
        queue: asyncio.Queue[LiveUpdate] = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[LiveUpdate]) -> None:
        self._subscribers.discard(queue)

    def _publish(self) -> None:
        update = self.live_update()
        for queue in self._subscribers:
            # A slow client only needs the newest update: drop any unsent one.
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(update)

    async def poll_once(self) -> None:
        try:
            services = await self.source.fetch()
        except Exception as exc:  # noqa: BLE001 — never let one bad poll stop the loop
            self.last_error = repr(exc)
            log.warning("%s fetch failed: %r", self.source.name, exc)
        else:
            now = datetime.now(UTC)
            self.snapshot = self.tracker.update(services, now)
            self.last_success = now
            self.last_error = None
            self._log_snapshot(len(services))
        self._publish()

    async def run(self) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(self.interval_s)

    def _log_snapshot(self, n_services: int) -> None:
        snap = self.snapshot
        assert snap is not None
        names = {s.id: s.name for s in self.geometry.stations}
        log.info(
            "%s: %d trains on route, %d to pass the bridge",
            self.source.name,
            n_services,
            len(snap.trains),
        )
        for t in snap.trains:
            delta = int((t.t_bridge - snap.generated_at).total_seconds())
            mins, secs = divmod(abs(delta), 60)
            log.info(
                "  %-4s → %-24s bridge %s (in %s%d:%02d)  [%s dep %s → %s arr %s]",
                t.direction,
                t.destination,
                f"{t.t_bridge.astimezone(LONDON):%H:%M:%S}",
                "-" if delta < 0 else "",
                mins,
                secs,
                names[t.prev.station_id],
                f"{t.prev.dep.astimezone(LONDON):%H:%M:%S}" if t.prev.dep else "?",
                names[t.next.station_id],
                f"{t.next.arr.astimezone(LONDON):%H:%M}" if t.next.arr else "?",
            )
