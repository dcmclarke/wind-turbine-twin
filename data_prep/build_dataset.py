"""
Build the 10-minute SCADA dataset from the raw ETH Zurich AV-7 HDF5 files.

Why 10-minute data:
    Wind turbine SCADA systems report 10-minute statistics, and the IEA Wind
    Task 19 icing method is defined on 10-minute means. The raw WM channels
    are sampled at ~7 Hz, so one 10-minute block holds ~4,200 readings.
    Aggregating turns ~30 GB of HDF5 into a ~100 KB CSV that is small enough
    to commit, so the evaluation and the demo run without the raw download.

What goes in:
    data/aventa_normal_operation_for_system_identification/*.hdf5
    data/aventa_rotor_icing/*.hdf5
    Five dates appear in both folders as byte-identical files, so each date
    is read once.

What comes out:
    backend/app/data/av7_10min.csv — one row per complete 10-minute block.

Period labels come from the dataset's own README: 17-20 December 2022 is
the rotor icing period; every other date is clean-blade reference data.

Usage:
    python data_prep/build_dataset.py
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path

import h5py
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
DATA_DIRS = [
    ROOT / "data" / "aventa_normal_operation_for_system_identification",
    ROOT / "data" / "aventa_rotor_icing",
]
OUTPUT = ROOT / "backend" / "app" / "data" / "av7_10min.csv"

ICING_DATES = {"17_12_2022", "18_12_2022", "19_12_2022", "20_12_2022"}

# Blocks shorter than this are partial recordings (logger restarts) and are
# not valid 10-minute samples.
MIN_BLOCK_SECONDS = 540

SENTINEL = -999  # the dataset marks bad readings as -1,000,000

COLUMNS = [
    "timestamp", "period", "wind_mean", "wind_std", "power_mean", "power_std",
    "power_min", "power_max", "rpm_median", "status_mode", "generating_frac",
    "n_samples", "duration_s",
]


# ── Aggregation ───────────────────────────────────────────────────────────────

def valid(values: np.ndarray) -> np.ndarray:
    """Drop sentinel values."""
    return values[values > SENTINEL]


def aggregate_block(group: h5py.Group) -> dict | None:
    """
    Reduce one 10-minute block of ~7 Hz readings to summary statistics.

    Returns None if the block is missing the WM channels or is too short.
    """
    try:
        wind = group["WM2/Value"][:].flatten()
        power = group["WM3/Value"][:].flatten()
        rpm = group["WM1/Value"][:].flatten()
        status = group["WM5/Value"][:].flatten()
        time = group["WM2/Time"][:].flatten()
    except KeyError:
        return None

    duration = float(time[-1]) if len(time) else 0.0
    if duration < MIN_BLOCK_SECONDS:
        return None

    # Wind and power must both be valid for a reading to count
    n = min(len(wind), len(power))
    keep = (wind[:n] > SENTINEL) & (power[:n] > SENTINEL)
    wind, power = wind[:n][keep], power[:n][keep]
    if len(wind) == 0:
        return None

    status = valid(status)
    codes, counts = np.unique(status, return_counts=True)

    # About a fifth of RPM samples are spurious exact zeros while the rotor is
    # turning (power is unaffected). The median ignores them; the mean would not.
    rpm = valid(rpm)

    return {
        "wind_mean": round(float(wind.mean()), 3),
        "wind_std": round(float(wind.std()), 3),
        "power_mean": round(float(power.mean()), 4),
        "power_std": round(float(power.std()), 4),
        "power_min": round(float(power.min()), 3),
        "power_max": round(float(power.max()), 3),
        "rpm_median": round(float(np.median(rpm)), 1) if len(rpm) else "",
        "status_mode": int(codes[counts.argmax()]) if len(codes) else "",
        "generating_frac": round(float((status == 10).mean()), 3) if len(status) else "",
        "n_samples": int(len(wind)),
        "duration_s": round(duration, 1),
    }


def file_date(path: Path) -> str:
    """Aventa_Taggenberg_17_12_2022.hdf5 -> '17_12_2022'."""
    return "_".join(path.stem.split("_")[-3:])


def block_start(date_key: str, block_name: str) -> datetime:
    """Combine the file date and the block name (HH_MM_SS) into a timestamp."""
    day = datetime.strptime(date_key, "%d_%m_%Y")
    h, m, s = (int(x) for x in block_name.split("_"))
    return day + timedelta(hours=h, minutes=m, seconds=s)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    files: dict[str, Path] = {}
    for folder in DATA_DIRS:
        for path in sorted(folder.glob("*.hdf5")):
            files.setdefault(file_date(path), path)  # duplicates are identical

    rows = []
    skipped = 0
    for date_key, path in sorted(files.items(), key=lambda kv: block_start(kv[0], "00_00_00")):
        period = "icing" if date_key in ICING_DATES else "clean"
        with h5py.File(path, "r") as f:
            for block in sorted(f["Aventa"].keys()):
                stats = aggregate_block(f[f"Aventa/{block}"])
                if stats is None:
                    skipped += 1
                    continue
                ts = block_start(date_key, block)
                rows.append({"timestamp": ts.isoformat(), "period": period, **stats})
        print(f"{path.name}: {period}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} ten-minute intervals written to {OUTPUT.relative_to(ROOT)}")
    print(f"{skipped} blocks skipped (missing WM channels or shorter than {MIN_BLOCK_SECONDS} s)")


if __name__ == "__main__":
    main()
