"""
Ingestion: run readings through the detector and store the outcome.

For each reading, everything it causes — the reading itself, any event it
opens, extends or closes, and the detector's updated memory — is committed
in one transaction. If anything fails, none of it is saved, so the stored
events and the detector's state can never disagree.
"""

import json
import threading
from collections.abc import Iterable

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.detector.reference_curve import ReferenceCurve
from app.detector.t19 import DetectorState, Event, IcingDetector, Sample, T19Config
from app.models import DetectorStateRow, IceEvent, Reading
from app.schemas import ReadingIn

CURVE = ReferenceCurve.load()
CFG = T19Config()

# One writer at a time: the demo feed or MQTT thread, and HTTP requests,
# must not interleave updates to the detector's state. This only covers one
# process; across processes, the unique timestamp in the database still
# stops a reading being stored twice (see ingest).
_write_lock = threading.Lock()


class DuplicateReading(Exception):
    pass


class OutOfOrderReading(Exception):
    pass


def load_state(db: Session) -> DetectorState:
    row = db.get(DetectorStateRow, 1)
    return DetectorState.from_dict(json.loads(row.state)) if row else DetectorState()


class _Ingestor:
    """Applies readings to one database session. Not thread-safe on its own."""

    def __init__(self, db: Session):
        self.db = db
        self.detector = IcingDetector(CURVE, CFG, load_state(db))
        self.active = db.scalar(select(IceEvent).where(IceEvent.ended_at.is_(None)))

    def apply(self, data: ReadingIn, source: str) -> Reading:
        sample = Sample(data.timestamp, data.wind_mean, data.power_mean, data.temperature)
        try:
            result = self.detector.process(sample)
        except ValueError as e:
            raise OutOfOrderReading(str(e)) from e

        if result.closed is not None and self.active is not None:
            _copy_event(result.closed, self.active)
            self.active = None

        if result.opened is not None:
            self.active = IceEvent()
            _copy_event(result.opened, self.active)
            self.db.add(self.active)
            self.db.flush()  # assigns the event id
            # The event is back-dated to the start of its run, so readings
            # already stored for that run belong to it too.
            self.db.execute(
                update(Reading)
                .where(Reading.timestamp >= result.opened.started_at, Reading.timestamp < sample.timestamp)
                .values(event_id=self.active.id)
            )
        elif result.active is not None and self.active is not None:
            _copy_event(result.active, self.active)

        ref = result.reference
        reading = Reading(
            timestamp=data.timestamp,
            wind_mean=data.wind_mean,
            wind_std=data.wind_std,
            power_mean=data.power_mean,
            rpm_median=data.rpm_median,
            status_mode=data.status_mode,
            temperature=data.temperature,
            flag=result.flag.value,
            p10=round(ref.p10, 4) if ref else None,
            p50=round(ref.p50, 4) if ref else None,
            p90=round(ref.p90, 4) if ref else None,
            loss_kwh=round(result.loss_kwh, 4),
            event_id=self.active.id if result.active is not None and self.active is not None else None,
            source=source,
        )
        self.db.add(reading)
        return reading

    def save_state(self) -> None:
        data = json.dumps(self.detector.state.to_dict())
        row = self.db.get(DetectorStateRow, 1)
        if row is None:
            self.db.add(DetectorStateRow(id=1, state=data))
        else:
            row.state = data


def _copy_event(event: Event, row: IceEvent) -> None:
    row.event_class = event.event_class
    row.started_at = event.started_at
    row.last_seen_at = event.last_seen_at
    row.ended_at = event.ended_at
    row.samples = event.samples
    row.energy_lost_kwh = round(event.energy_lost_kwh, 4)
    row.mean_wind = round(event.mean_wind, 3)


# ── Public API ────────────────────────────────────────────────────────────────

def ingest(db: Session, data: ReadingIn, source: str) -> Reading:
    """Process and store one reading. Raises DuplicateReading or OutOfOrderReading."""
    with _write_lock:
        if _is_stored(db, data):
            raise DuplicateReading(f"Reading at {data.timestamp} already stored")
        ingestor = _Ingestor(db)
        try:
            reading = ingestor.apply(data, source)
            ingestor.save_state()
            db.commit()
        except IntegrityError:
            db.rollback()
            # Another process stored the same reading since the check above
            if _is_stored(db, data):
                raise DuplicateReading(f"Reading at {data.timestamp} already stored") from None
            raise
        except Exception:
            db.rollback()
            raise
        db.refresh(reading)
        return reading


def _is_stored(db: Session, data: ReadingIn) -> bool:
    return db.scalar(select(Reading.id).where(Reading.timestamp == data.timestamp)) is not None


def ingest_many(db: Session, items: Iterable[ReadingIn], source: str) -> int:
    """Process a batch in one transaction (used to preload history quickly)."""
    with _write_lock:
        ingestor = _Ingestor(db)
        count = 0
        try:
            for data in items:
                ingestor.apply(data, source)
                count += 1
            ingestor.save_state()
            db.commit()
        except Exception:
            db.rollback()
            raise
        return count


def reset(db: Session) -> None:
    """Delete all readings, events and detector state."""
    with _write_lock:
        db.execute(delete(Reading))
        db.execute(delete(IceEvent))
        db.execute(delete(DetectorStateRow))
        db.commit()
