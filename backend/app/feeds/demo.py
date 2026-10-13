"""
Demo feed: replays the bundled AV-7 dataset through the real ingestion path.

The hosted demo has no MQTT broker, so this thread stands in for the edge
gateway. Each loop it clears the tables, loads everything before
DEMO_LIVE_FROM in one batch (so a visitor sees history immediately), then
streams the remaining readings one at a time, DEMO_SECONDS_PER_SAMPLE apart.
"""

import logging
import threading

from app.config import Settings
from app.dataset import Row, load_rows
from app.database import SessionLocal
from app.schemas import ReadingIn
from app.services.ingest import ingest, ingest_many, reset

log = logging.getLogger(__name__)

PAUSE_BETWEEN_LOOPS = 30  # seconds the final state stays on screen


def to_reading(row: Row) -> ReadingIn:
    return ReadingIn(
        timestamp=row.timestamp,
        wind_mean=row.wind_mean,
        wind_std=row.wind_std,
        power_mean=row.power_mean,
        rpm_median=row.rpm_median,
        status_mode=row.status_mode,
    )


class DemoFeed(threading.Thread):
    def __init__(self, settings: Settings):
        super().__init__(name="demo-feed", daemon=True)
        self.interval = settings.demo_seconds_per_sample
        self.live_from = settings.demo_live_from
        self.rows = load_rows()
        self.loop = 0
        self.position = 0
        self._stopping = threading.Event()

    @property
    def total(self) -> int:
        return len(self.rows)

    def stop(self) -> None:
        self._stopping.set()

    def run(self) -> None:
        while not self._stopping.is_set():
            try:
                self._play_once()
            except Exception:
                log.exception("Demo feed failed; restarting in 10 s")
                self._stopping.wait(10)

    def _play_once(self) -> None:
        self.loop += 1
        history = [r for r in self.rows if r.timestamp < self.live_from]
        live = [r for r in self.rows if r.timestamp >= self.live_from]

        with SessionLocal() as db:
            log.warning("Demo loop %d: deleting all readings and events to start the replay", self.loop)
            reset(db)
            ingest_many(db, (to_reading(r) for r in history), source="demo")
        self.position = len(history)
        log.info("Demo loop %d: preloaded %d readings, streaming %d", self.loop, len(history), len(live))

        for row in live:
            if self._stopping.wait(self.interval):
                return
            with SessionLocal() as db:
                ingest(db, to_reading(row), source="demo")
            self.position += 1

        self._stopping.wait(PAUSE_BETWEEN_LOOPS)
