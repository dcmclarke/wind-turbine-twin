from sqlalchemy import Column, Integer, Float, DateTime, Boolean, String
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone
from pydantic import BaseModel


# SQLAlchemy Base - all database table classes inherit from this
class Base(DeclarativeBase):
    pass

# DATABASE TABLES

class TurbineReading(Base):
    """
    One SCADA reading from the turbine.
    Stored every time a reading is ingested via POST /api/telemetry.
    """
    __tablename__ = "turbine_readings"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    timestamp    = Column(DateTime, nullable=False)
    wind_speed   = Column(Float, nullable=False)   # m/s  — WM2
    power_output = Column(Float, nullable=False)   # kW   — WM3
    rpm          = Column(Float, nullable=True)    # RPM  — WM1 (nullable: not always needed)
    yaw_angle    = Column(Float, nullable=True)    # deg  — WM4
    rotor_status = Column(Float, nullable=True)    # code — WM5
    power_ratio  = Column(Float, nullable=True)    # calculated by detector

class IcingEvent(Base):
    __tablename__ = "icing_events"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    started_at    = Column(DateTime, nullable=False)
    last_seen_at  = Column(DateTime, nullable=False)
    trigger_count = Column(Integer, nullable=False)
    is_active     = Column(Boolean, default=True, nullable=False)


# PYDANTIC SCHEMAS
# define what JSON looks like going in/out of API
# FastAPI uses these to validate requests & serialise responses.

class TelemetryInput(BaseModel):
    """
    What the ingestion script sends us per SCADA reading. All fields from the AV-7 WM channels.
    Timestamp is a string so it survives JSON serialisation cleanly
    """
    timestamp:    str    # ISO format: "2022-12-17T16:02:23"
    wind_speed:   float  # m/s
    power_output: float  # kW
    rpm:          float  # RPM
    yaw_angle:    float  # degrees
    rotor_status: float  # status code


class TelemetryOutput(BaseModel):
    """What we send back after ingesting a reading."""
    id:           int
    timestamp:    datetime
    wind_speed:   float
    power_output: float
    rpm:          float | None
    yaw_angle:    float | None
    rotor_status: float | None
    power_ratio:  float | None

    model_config = {"from_attributes": True}


class IcingStatusOutput(BaseModel):
    """Current icing detection state — returned by GET /api/icing/status."""
    is_icing:      bool
    trigger_count: int
    window_fill:   int
    last_ratio:    float | None


class IcingEventOutput(BaseModel):
    """A single logged icing event — returned by GET /api/icing/history."""
    id:            int
    started_at:    datetime
    last_seen_at:  datetime
    trigger_count: int
    is_active:     bool

    model_config = {"from_attributes": True}


