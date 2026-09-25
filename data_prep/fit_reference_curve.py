"""
Fit the clean-blade reference power curve used by the running service.

Reads the bundled 10-minute dataset, keeps the reference rows (clean blades,
turbine generating, power >= 1 % of rated) and writes
backend/app/detector/reference_curve.json.

The evaluation does NOT use this file: it refits the curve for every held-out
day so the day being tested never helped build its own reference.

Usage:
    python data_prep/fit_reference_curve.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.dataset import is_reference, load_rows  # noqa: E402
from app.detector.reference_curve import DEFAULT_PATH, ReferenceCurve  # noqa: E402


def main():
    rows = load_rows()
    reference = [(r.wind_mean, r.power_mean) for r in rows if is_reference(r)]
    curve = ReferenceCurve.fit(reference)
    curve.save()

    low, high = curve.wind_range
    print(f"{len(reference)} reference intervals -> {len(curve.bins)} bins, valid {low:.2f}-{high:.2f} m/s")
    for b in curve.bins:
        print(f"  {b.wind_speed:5.2f} m/s  P10={b.p10:5.2f}  P50={b.p50:5.2f}  P90={b.p90:5.2f} kW  (n={b.samples})")
    print(f"Saved {DEFAULT_PATH}")


if __name__ == "__main__":
    main()
