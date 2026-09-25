"""
The bundled 10-minute AV-7 dataset (built by data_prep/build_dataset.py).

Source: Chatzi, Abdallah, Hofsäß, Bischoff, Barber, Marykovskiy (2023).
Aventa AV-7 ETH Zurich Research Wind Turbine SCADA and SHM data.
Zenodo, https://doi.org/10.5281/zenodo.8223010 — licensed CC BY 4.0.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.detector.t19 import Sample, T19Config

DATASET_PATH = Path(__file__).parent / "data" / "av7_10min.csv"


@dataclass(frozen=True)
class Row:
    timestamp: datetime
    period: str             # "clean" or "icing", per the dataset's own README
    wind_mean: float
    wind_std: float
    power_mean: float
    rpm_median: float | None
    status_mode: int | None
    generating_frac: float | None

    @property
    def day(self) -> str:
        return self.timestamp.date().isoformat()

    def to_sample(self) -> Sample:
        # The AV-7 temperature sensor is broken for the whole dataset,
        # so no temperature is passed on.
        return Sample(self.timestamp, self.wind_mean, self.power_mean)


def _float(value: str) -> float | None:
    return float(value) if value != "" else None


def load_rows(path: Path = DATASET_PATH) -> list[Row]:
    with open(path, newline="") as f:
        return [
            Row(
                timestamp=datetime.fromisoformat(r["timestamp"]),
                period=r["period"],
                wind_mean=float(r["wind_mean"]),
                wind_std=float(r["wind_std"]),
                power_mean=float(r["power_mean"]),
                rpm_median=_float(r["rpm_median"]),
                status_mode=int(r["status_mode"]) if r["status_mode"] else None,
                generating_frac=_float(r["generating_frac"]),
            )
            for r in csv.DictReader(f)
        ]


def is_reference(row: Row, cfg: T19Config = T19Config()) -> bool:
    """
    Whether a row may be used to build the clean-blade reference curve.

    Task 19 keeps normal-operation data above +3 °C with power >= 1 % of
    rated. Without a temperature signal, "clean" comes from the dataset's
    own labelling; "normal operation" means the turbine reported the
    generating status (10) for at least 95 % of the interval.
    """
    return (
        row.period == "clean"
        and row.generating_frac is not None
        and row.generating_frac >= 0.95
        and row.power_mean >= cfg.power_level * cfg.rated_power
    )
