"""
Reference (non-iced) power curve, as defined by the IEA Wind Task 19 method.

The turbine's own clean-blade data is binned by wind speed. For each bin we
keep the median wind speed, the median power (P50) and the 10th and 90th
percentiles of power (P10, P90). A 10-minute reading is later judged against
these values, interpolated to its wind speed:

    power below P10  -> underproduction (possible ice on the blades)
    power above P90  -> overproduction  (possible ice on the anemometer)

Deliberate difference from the Task 19 defaults:
    Task 19 drops bins with fewer than 36 samples (6 hours of data), which
    assumes a year of SCADA history. The public AV-7 data has 187 usable
    clean 10-minute samples, so the minimum is lowered to 10 and the curve
    only covers the wind speeds those bins span. Outside that range the
    detector reports "no reference" instead of extrapolating.
    See docs/decisions.md (Decision 10).
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "reference_curve.json"


@dataclass(frozen=True)
class CurveBin:
    wind_speed: float   # median wind speed of the samples in this bin, m/s
    p10: float          # kW
    p50: float          # kW
    p90: float          # kW
    samples: int


@dataclass(frozen=True)
class Reference:
    """Expected power at one wind speed."""
    p10: float
    p50: float
    p90: float


def percentile(values: list[float], pct: float) -> float:
    """
    Percentile with linear interpolation between neighbouring values
    (the same definition as numpy.percentile and scipy's scoreatpercentile).
    """
    ordered = sorted(values)
    position = (len(ordered) - 1) * pct / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def median(values: list[float]) -> float:
    return percentile(values, 50)


class ReferenceCurve:
    def __init__(self, bins: list[CurveBin], bin_width: float):
        if not bins:
            raise ValueError("A reference curve needs at least one bin")
        self.bins = sorted(bins, key=lambda b: b.wind_speed)
        self.bin_width = bin_width

    # ── Fitting ───────────────────────────────────────────────────────────────

    @classmethod
    def fit(
        cls,
        samples: list[tuple[float, float]],
        bin_width: float = 0.5,
        min_samples: int = 10,
    ) -> "ReferenceCurve":
        """
        Build the curve from clean-blade (wind_mean, power_mean) pairs.

        The caller decides what counts as clean reference data; Task 19 uses
        normal-operation periods above +3 °C with power >= 1 % of rated.
        """
        grouped: dict[float, list[tuple[float, float]]] = {}
        for wind, power in samples:
            centre = round(round(wind / bin_width) * bin_width, 3)
            grouped.setdefault(centre, []).append((wind, power))

        bins = []
        for centre, members in grouped.items():
            if len(members) < min_samples:
                continue
            winds = [w for w, _ in members]
            powers = [p for _, p in members]
            bins.append(CurveBin(
                wind_speed=round(median(winds), 3),
                p10=round(percentile(powers, 10), 4),
                p50=round(median(powers), 4),
                p90=round(percentile(powers, 90), 4),
                samples=len(members),
            ))
        return cls(bins, bin_width)

    # ── Lookup ────────────────────────────────────────────────────────────────

    @property
    def wind_range(self) -> tuple[float, float]:
        """Wind speeds the curve has evidence for: the outer edges of its bins."""
        half = self.bin_width / 2
        return self.bins[0].wind_speed - half, self.bins[-1].wind_speed + half

    def covers(self, wind_speed: float) -> bool:
        low, high = self.wind_range
        return low <= wind_speed <= high

    def at(self, wind_speed: float) -> Reference | None:
        """
        P10/P50/P90 at this wind speed, linearly interpolated between bin
        medians (as Task 19 does with numpy.interp). None outside the range.
        """
        if not self.covers(wind_speed):
            return None

        first, last = self.bins[0], self.bins[-1]
        if wind_speed <= first.wind_speed:
            return Reference(first.p10, first.p50, first.p90)
        if wind_speed >= last.wind_speed:
            return Reference(last.p10, last.p50, last.p90)

        for left, right in zip(self.bins, self.bins[1:]):
            if left.wind_speed <= wind_speed <= right.wind_speed:
                t = (wind_speed - left.wind_speed) / (right.wind_speed - left.wind_speed)
                return Reference(
                    p10=left.p10 + t * (right.p10 - left.p10),
                    p50=left.p50 + t * (right.p50 - left.p50),
                    p90=left.p90 + t * (right.p90 - left.p90),
                )
        return None  # unreachable: the loop covers every point in range

    # ── Persistence ───────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        low, high = self.wind_range
        return {
            "bin_width": self.bin_width,
            "wind_range": [round(low, 3), round(high, 3)],
            "bins": [asdict(b) for b in self.bins],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReferenceCurve":
        return cls([CurveBin(**b) for b in data["bins"]], data["bin_width"])

    def save(self, path: Path = DEFAULT_PATH) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "ReferenceCurve":
        return cls.from_dict(json.loads(path.read_text()))
