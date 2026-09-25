"""
Pydantic schemas: the JSON going in and out of the API and over MQTT.
Validation here stops malformed sensor data before it reaches the detector.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReadingIn(BaseModel):
    """One 10-minute SCADA summary, as published by the edge gateway."""
    timestamp: datetime
    wind_mean: float = Field(ge=0, le=60, description="10-minute mean wind speed, m/s")
    wind_std: float | None = Field(default=None, ge=0)
    power_mean: float = Field(ge=-5, le=20, description="10-minute mean power, kW")
    rpm_median: float | None = Field(default=None, ge=0, le=200)
    status_mode: int | None = None
    temperature: float | None = Field(default=None, ge=-60, le=60, description="°C; omit when unavailable")


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    wind_mean: float
    power_mean: float
    rpm_median: float | None
    status_mode: int | None
    flag: str
    p10: float | None
    p50: float | None
    p90: float | None
    loss_kwh: float
    event_id: int | None
    received_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_class: str
    started_at: datetime
    last_seen_at: datetime
    ended_at: datetime | None
    samples: int
    energy_lost_kwh: float
    mean_wind: float
    is_active: bool


class RunOut(BaseModel):
    """A flag building towards an event but not yet confirmed."""
    flag: str
    length: int
    required: int


class FeedOut(BaseModel):
    mode: str
    seconds_per_sample: float | None = None
    speedup: float | None = None
    loop: int | None = None
    position: int | None = None
    total: int | None = None


class TotalsOut(BaseModel):
    readings: int
    events: int
    energy_lost_kwh: float


class StatusOut(BaseModel):
    feed: FeedOut
    latest: ReadingOut | None
    active_event: EventOut | None
    run: RunOut | None
    totals: TotalsOut
    reference_range: tuple[float, float]


class DashboardOut(BaseModel):
    """Everything the dashboard needs in one poll."""
    status: StatusOut
    readings: list[ReadingOut]
    events: list[EventOut]


class CurveBinOut(BaseModel):
    wind_speed: float
    p10: float
    p50: float
    p90: float
    samples: int


class ReferenceCurveOut(BaseModel):
    bin_width: float
    wind_range: tuple[float, float]
    bins: list[CurveBinOut]
    icing_samples: int
    stop_samples: int
    rated_power: float
