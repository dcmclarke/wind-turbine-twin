"""
Streaming icing detector following the IEA Wind Task 19 method.

Reference: IEA Wind TCP Task 19, "T19IceLossMethod"
https://github.com/IEAWind-Task19/T19IceLossMethod (BSD-3-Clause)

Each 10-minute sample is first given a flag by comparing its power to the
reference curve at its wind speed:

    underproduction  power <= P10, turbine still producing   -> candidate class A
    stopped          power < 1 % of rated while P50 says it
                     should be producing                     -> candidate class B
    overproduction   power >= P90                            -> candidate class C
    normal           none of the above
    no_reference     wind speed outside the reference curve
    too_warm         temperature known and above +1 °C (icing impossible)

A flag only becomes an icing *event* once it persists:
    A and C need 3 consecutive samples (30 minutes)
    B needs 6 consecutive samples (60 minutes)
Once confirmed, the event is back-dated to the first sample of the run, as
Task 19 does. It ends at the first sample that no longer carries its flag.

Energy lost is (P50 - actual power) x 10 minutes, summed over the event's
samples (classes A and B only; for C the power reading is fine, the wind
reading is not).

Differences from the reference implementation (see docs/decisions.md):
  - Samples arrive one at a time, so the B stop test cannot look ahead the
    way the batch implementation does.
  - The AV-7 temperature sensor is broken, so on this dataset the +1 °C
    condition is skipped. The code applies it whenever a temperature is given.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from app.detector.reference_curve import Reference, ReferenceCurve

SAMPLE_LENGTH = timedelta(minutes=10)


class Flag(str, Enum):
    NORMAL = "normal"
    UNDERPRODUCTION = "underproduction"
    STOPPED = "stopped"
    OVERPRODUCTION = "overproduction"
    NO_REFERENCE = "no_reference"
    TOO_WARM = "too_warm"


EVENT_CLASS = {
    Flag.UNDERPRODUCTION: "A",
    Flag.STOPPED: "B",
    Flag.OVERPRODUCTION: "C",
}


@dataclass(frozen=True)
class T19Config:
    rated_power: float = 7.0         # kW, AV-7 nameplate
    icing_samples: int = 3           # Task 19 "icing time"
    stop_samples: int = 6            # Task 19 "stop time filter"
    stop_limit: float = 0.005        # fraction of rated: reference must exceed this for a stop to count
    power_level: float = 0.01        # fraction of rated: below this the turbine counts as stopped
    icing_temperature: float = 1.0   # °C
    max_gap_seconds: int = 660       # samples further apart are not consecutive (AV-7 blocks are 601 s apart)

    def samples_required(self, flag: Flag) -> int:
        return self.stop_samples if flag == Flag.STOPPED else self.icing_samples


@dataclass(frozen=True)
class Sample:
    """One 10-minute SCADA summary."""
    timestamp: datetime
    wind_mean: float                 # m/s
    power_mean: float                # kW
    temperature: float | None = None # °C, None when no working sensor


@dataclass
class Event:
    event_class: str                 # "A", "B" or "C"
    started_at: datetime
    last_seen_at: datetime
    samples: int = 0
    energy_lost_kwh: float = 0.0
    wind_sum: float = 0.0
    ended_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    @property
    def mean_wind(self) -> float:
        return self.wind_sum / self.samples if self.samples else 0.0

    def add(self, timestamp: datetime, wind_mean: float, loss_kwh: float) -> None:
        self.last_seen_at = timestamp
        self.samples += 1
        self.energy_lost_kwh += loss_kwh
        self.wind_sum += wind_mean

    def close(self) -> None:
        self.ended_at = self.last_seen_at + SAMPLE_LENGTH


@dataclass
class Result:
    """What the detector concluded about one sample."""
    flag: Flag
    reference: Reference | None
    loss_kwh: float
    run_flag: Flag | None            # flag currently building towards an event
    run_length: int                  # how many samples in a row carry it
    run_required: int                # how many are needed to confirm an event
    opened: Event | None = None      # event confirmed by this sample
    closed: Event | None = None      # event that ended just before this sample
    active: Event | None = None      # event in progress after this sample


# ── Per-sample classification ─────────────────────────────────────────────────

def classify(sample: Sample, curve: ReferenceCurve, cfg: T19Config) -> tuple[Flag, Reference | None]:
    """Compare one sample against the reference curve."""
    if sample.temperature is not None and sample.temperature > cfg.icing_temperature:
        return Flag.TOO_WARM, curve.at(sample.wind_mean)

    ref = curve.at(sample.wind_mean)
    if ref is None:
        return Flag.NO_REFERENCE, None

    power = sample.power_mean
    if power >= ref.p90:
        return Flag.OVERPRODUCTION, ref
    if power <= ref.p10:
        if power >= cfg.power_level * cfg.rated_power:
            return Flag.UNDERPRODUCTION, ref
        if ref.p50 >= cfg.stop_limit * cfg.rated_power:
            return Flag.STOPPED, ref
    return Flag.NORMAL, ref


def energy_shortfall(sample: Sample, flag: Flag, ref: Reference | None) -> float:
    """kWh the turbine should have produced in this sample but didn't."""
    if ref is None or flag not in (Flag.UNDERPRODUCTION, Flag.STOPPED):
        return 0.0
    hours = SAMPLE_LENGTH.total_seconds() / 3600
    return max(0.0, ref.p50 - sample.power_mean) * hours


# ── Streaming detector ────────────────────────────────────────────────────────

@dataclass
class _RunSample:
    timestamp: datetime
    wind_mean: float
    loss_kwh: float


@dataclass
class DetectorState:
    """Everything the detector remembers between samples. Serialisable."""
    last_timestamp: datetime | None = None
    run_flag: Flag | None = None
    run: list[_RunSample] = field(default_factory=list)
    active: Event | None = None

    def to_dict(self) -> dict:
        return {
            "last_timestamp": _iso(self.last_timestamp),
            "run_flag": self.run_flag.value if self.run_flag else None,
            "run": [{**asdict(r), "timestamp": _iso(r.timestamp)} for r in self.run],
            "active": _event_to_dict(self.active),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DetectorState":
        return cls(
            last_timestamp=_parse(data.get("last_timestamp")),
            run_flag=Flag(data["run_flag"]) if data.get("run_flag") else None,
            run=[_RunSample(_parse(r["timestamp"]), r["wind_mean"], r["loss_kwh"]) for r in data.get("run", [])],
            active=_event_from_dict(data.get("active")),
        )


class IcingDetector:
    def __init__(self, curve: ReferenceCurve, cfg: T19Config = T19Config(), state: DetectorState | None = None):
        self.curve = curve
        self.cfg = cfg
        self.state = state or DetectorState()

    def process(self, sample: Sample) -> Result:
        """Feed the next 10-minute sample. Samples must arrive in time order."""
        s = self.state
        if s.last_timestamp is not None and sample.timestamp <= s.last_timestamp:
            raise ValueError(f"Sample at {sample.timestamp} is not after {s.last_timestamp}")

        closed = None

        # A gap in the data breaks any run and ends any event
        if s.last_timestamp is not None:
            gap = (sample.timestamp - s.last_timestamp).total_seconds()
            if gap > self.cfg.max_gap_seconds:
                closed = self._close_active()
                self._reset_run()

        flag, ref = classify(sample, self.curve, self.cfg)
        loss = energy_shortfall(sample, flag, ref)
        opened = None

        if s.active is not None and EVENT_CLASS.get(flag) == s.active.event_class:
            s.active.add(sample.timestamp, sample.wind_mean, loss)
        else:
            if s.active is not None:
                closed = self._close_active()
            opened = self._extend_run(sample, flag, loss)

        s.last_timestamp = sample.timestamp
        return Result(
            flag=flag,
            reference=ref,
            loss_kwh=loss,
            run_flag=s.run_flag,
            run_length=len(s.run),
            run_required=self.cfg.samples_required(s.run_flag) if s.run_flag else 0,
            opened=opened,
            closed=closed,
            active=s.active,
        )

    # ── Internals ─────────────────────────────────────────────────────────────

    def _extend_run(self, sample: Sample, flag: Flag, loss: float) -> Event | None:
        """Grow the run of identical candidate flags; open an event once it is long enough."""
        s = self.state
        if flag not in EVENT_CLASS:
            self._reset_run()
            return None

        if flag != s.run_flag:
            self._reset_run()
            s.run_flag = flag
        s.run.append(_RunSample(sample.timestamp, sample.wind_mean, loss))

        if len(s.run) < self.cfg.samples_required(flag):
            return None

        event = Event(event_class=EVENT_CLASS[flag], started_at=s.run[0].timestamp, last_seen_at=s.run[0].timestamp)
        for r in s.run:
            event.add(r.timestamp, r.wind_mean, r.loss_kwh)
        s.active = event
        self._reset_run()
        return event

    def _close_active(self) -> Event | None:
        event = self.state.active
        if event is not None:
            event.close()
            self.state.active = None
        return event

    def _reset_run(self) -> None:
        self.state.run_flag = None
        self.state.run = []


def detect(samples: list[Sample], curve: ReferenceCurve, cfg: T19Config = T19Config()) -> tuple[list[Result], list[Event]]:
    """
    Run the detector over a whole series (used by the evaluation).

    Returns one Result per sample and every event found, including one still
    active at the end of the series.
    """
    detector = IcingDetector(curve, cfg)
    results, events = [], []
    for sample in samples:
        result = detector.process(sample)
        results.append(result)
        if result.opened is not None:
            events.append(result.opened)
    return results, events


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _event_to_dict(event: Event | None) -> dict | None:
    if event is None:
        return None
    data = asdict(event)
    for key in ("started_at", "last_seen_at", "ended_at"):
        data[key] = _iso(data[key])
    return data


def _event_from_dict(data: dict | None) -> Event | None:
    if data is None:
        return None
    return Event(
        event_class=data["event_class"],
        started_at=_parse(data["started_at"]),
        last_seen_at=_parse(data["last_seen_at"]),
        samples=data["samples"],
        energy_lost_kwh=data["energy_lost_kwh"],
        wind_sum=data["wind_sum"],
        ended_at=_parse(data.get("ended_at")),
    )
