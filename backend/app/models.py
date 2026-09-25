"""
Database tables.

Table names differ from version 1 (turbine_readings, icing_events) so a
database that still holds the old tables keeps working; the old ones can be
dropped.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Reading(Base):
    """One 10-minute SCADA summary and what the detector concluded about it."""
    __tablename__ = "scada_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # As recorded by the turbine (local time, no timezone). Unique so a
    # message delivered twice (MQTT QoS 1 is at-least-once) is stored once.
    timestamp: Mapped[datetime] = mapped_column(DateTime, unique=True, index=True)
    wind_mean: Mapped[float] = mapped_column(Float)
    wind_std: Mapped[float | None] = mapped_column(Float)
    power_mean: Mapped[float] = mapped_column(Float)
    rpm_median: Mapped[float | None] = mapped_column(Float)
    status_mode: Mapped[int | None] = mapped_column(Integer)
    temperature: Mapped[float | None] = mapped_column(Float)

    # Detector output
    flag: Mapped[str] = mapped_column(String(20))
    p10: Mapped[float | None] = mapped_column(Float)
    p50: Mapped[float | None] = mapped_column(Float)
    p90: Mapped[float | None] = mapped_column(Float)
    loss_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("ice_events.id"), index=True)

    source: Mapped[str] = mapped_column(String(10))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IceEvent(Base):
    """A confirmed icing event (Task 19 class A, B or C)."""
    __tablename__ = "ice_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_class: Mapped[str] = mapped_column(String(1))
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    samples: Mapped[int] = mapped_column(Integer)
    energy_lost_kwh: Mapped[float] = mapped_column(Float)
    mean_wind: Mapped[float] = mapped_column(Float)

    readings: Mapped[list[Reading]] = relationship()

    @property
    def is_active(self) -> bool:
        return self.ended_at is None


class DetectorStateRow(Base):
    """
    The detector's memory (current run and active event), saved in the same
    transaction as each reading so a restart resumes exactly where it stopped.
    """
    __tablename__ = "detector_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
