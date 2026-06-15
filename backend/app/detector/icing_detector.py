"""
Icing detector (IEA Wind Task 19 T19 method).

- Calculates power ratio = actual_power / expected_power (from power_curve)
- Uses a persistence filter: fires alert when MIN_TRIGGERS out of last
  WINDOW_SIZE readings are below RATIO_THRESHOLD.
- Temperature gate removed because AV-7 temperature sensor malfunctioned.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from app.detector.power_curve import power_ratio

# Tunable parameters – change these if needed after evaluation
RATIO_THRESHOLD = 0.1   # ratio below this = underperforming
WINDOW_SIZE     = 10    # number of recent readings to track
MIN_TRIGGERS    = 7     # how many of those must be below threshold to alert


@dataclass
class IcingReading:
    """Result of processing one SCADA reading."""
    wind_speed:   float
    actual_power: float
    power_ratio:  float | None   # None if wind below cut‑in
    is_icing:     bool
    trigger_count: int
    timestamp:    datetime


class IcingDetector:
    """Stateful detector with a rolling window (deque). One instance for the whole app."""

    def __init__(
        self,
        ratio_threshold: float = RATIO_THRESHOLD,
        window_size:     int   = WINDOW_SIZE,
        min_triggers:    int   = MIN_TRIGGERS,
    ):
        self.ratio_threshold = ratio_threshold
        self.window_size = window_size
        self.min_triggers = min_triggers
        self._window: deque[float] = deque(maxlen=window_size)

    def process(
        self,
        wind_speed: float,
        actual_power: float,
        timestamp: datetime | None = None,
    ) -> IcingReading:
        """Add a new reading and return current icing state."""
        ratio = power_ratio(actual_power, wind_speed)

        if ratio is not None:
            self._window.append(ratio)

        trigger_count = sum(1 for r in self._window if r < self.ratio_threshold)

        is_icing = (
            len(self._window) >= self.window_size
            and trigger_count >= self.min_triggers
        )

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return IcingReading(
            wind_speed=wind_speed,
            actual_power=actual_power,
            power_ratio=ratio,
            is_icing=is_icing,
            trigger_count=trigger_count,
            timestamp=timestamp,
        )

    def get_state(self) -> dict:
        """Return current window state without advancing."""
        trigger_count = sum(1 for r in self._window if r < self.ratio_threshold)
        return {
            "window_fill": len(self._window),
            "trigger_count": trigger_count,
            "is_icing": (
                len(self._window) >= self.window_size
                and trigger_count >= self.min_triggers
            ),
        }

    def reset(self) -> None:
        """Clear the rolling window (used between test runs)."""
        self._window.clear()

    @property
    def window_fill(self) -> int:
        """Number of readings currently in the window."""
        return len(self._window)
