"""
Reproduce the first version's evaluation and show why it was misleading.

Version 1 of this project scored a per-reading detector (~7 Hz data, alarm
when 7 of the last 10 power ratios fell below 0.1) and reported
precision 0.757 / recall 1.000 / F1 0.862. This script re-implements that
detector and its evaluation exactly, then adds the checks it was missing.

Findings (see evaluation/results/legacy_metrics.json):
  - Every reading labelled "icing" has power exactly 0.0, so a detector
    that flags near-zero power reaches recall 1.000 by construction.
  - A one-line rule "alarm if power <= 0" scores as well or better.
  - Negative examples from the normal-operation files were first filtered
    to status 10 ("generating"), which removed idle periods that would have
    been false alarms.
  - Five normal days appear in both source folders (byte-identical files)
    and were counted twice.

Needs the raw HDF5 data in data/ (about 30 GB, see data/README.md), so it
does not run in CI. Takes a few minutes.

Usage:
    python evaluation/legacy_comparison.py
"""

import json
from collections import deque
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ICING = ROOT / "data" / "aventa_rotor_icing"
NORMAL = ROOT / "data" / "aventa_normal_operation_for_system_identification"
OUTPUT = Path(__file__).parent / "results" / "legacy_metrics.json"

ICING_DATES = {"17_12_2022", "18_12_2022"}
EXCLUDE_DATES = {"19_12_2022", "20_12_2022"}
CUT_IN = 2.0

# Version 1 power curve: nearest 0.5 m/s bin, mean power (kW)
V1_CURVE = {
    2.0: 0.453, 2.5: 0.871, 3.0: 1.533, 3.5: 2.323, 4.0: 3.339, 4.5: 4.426, 5.0: 5.287,
    5.5: 5.902, 6.0: 6.410, 6.5: 6.673, 7.0: 6.779, 7.5: 6.870, 8.0: 6.880, 8.5: 6.874,
    9.0: 6.859, 9.5: 6.848, 10.0: 6.827, 10.5: 6.864, 11.0: 6.781, 11.5: 6.656,
    12.0: 6.837, 12.5: 6.849, 13.0: 6.837, 13.5: 6.832, 14.0: 6.811,
}


def v1_ratio(power: float, wind: float) -> float | None:
    if wind < 2.0 or wind > 14.0:
        return None
    return power / V1_CURVE[round(round(wind / 0.5) * 0.5, 1)]


def v1_detect(readings: np.ndarray) -> np.ndarray:
    """7-of-10 persistence filter on power ratios below 0.1."""
    window: deque = deque(maxlen=10)
    alarms = np.zeros(len(readings), dtype=bool)
    for i, (wind, power, _) in enumerate(readings):
        ratio = v1_ratio(power, wind)
        if ratio is not None:
            window.append(ratio)
        alarms[i] = len(window) == 10 and sum(r < 0.1 for r in window) >= 7
    return alarms


def load(path: Path) -> np.ndarray:
    """(wind, power, status) per reading, dropping sentinel values like v1 did."""
    chunks = []
    with h5py.File(path, "r") as f:
        for block in f["Aventa"].keys():
            try:
                w = f[f"Aventa/{block}/WM2/Value"][:].flatten()
                p = f[f"Aventa/{block}/WM3/Value"][:].flatten()
                s = f[f"Aventa/{block}/WM5/Value"][:].flatten()
            except KeyError:
                continue
            n = min(len(w), len(p), len(s))
            w, p, s = w[:n], p[:n], s[:n]
            keep = (w >= -999) & (p >= -999)
            chunks.append(np.column_stack([w[keep], p[keep], s[keep]]))
    return np.vstack(chunks)


def date_of(path: Path) -> str:
    return "_".join(path.stem.split("_")[-3:])


def scores(y: np.ndarray, pred: np.ndarray) -> dict:
    tp = int((y & pred).sum()); fp = int((~y & pred).sum()); fn = int((y & ~pred).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "TP": tp, "FP": fp, "FN": fn}


def main():
    print("Loading raw data (a few minutes)...")
    normal_files = sorted(NORMAL.glob("*.hdf5"))
    icing_files = sorted(ICING.glob("*.hdf5"))
    normal_raw = np.vstack([load(f) for f in normal_files])
    other_months = np.vstack([load(f) for f in icing_files if date_of(f) not in ICING_DATES | EXCLUDE_DATES])
    icing_raw = np.vstack([load(f) for f in icing_files if date_of(f) in ICING_DATES])

    # Version 1 labelling, exactly as in the original evaluate.py
    neg_a = normal_raw[(normal_raw[:, 2] == 10) & (normal_raw[:, 0] >= CUT_IN)]
    neg_b = other_months[(other_months[:, 0] >= CUT_IN) & (other_months[:, 1] >= 0)]
    negatives = np.vstack([neg_a, neg_b])
    positives = icing_raw[icing_raw[:, 0] >= CUT_IN]
    y = np.r_[np.zeros(len(negatives), bool), np.ones(len(positives), bool)]

    v1 = np.r_[v1_detect(negatives), v1_detect(positives)]
    zero_power = np.r_[negatives[:, 1] <= 0.0, positives[:, 1] <= 0.0]

    # What changes if the idle readings are left in the normal-operation files
    neg_all = normal_raw[normal_raw[:, 0] >= CUT_IN]
    y_all = np.r_[np.zeros(len(neg_all), bool), np.ones(len(positives), bool)]
    v1_all = np.r_[v1_detect(neg_all), v1_detect(positives)]

    duplicated = sorted({date_of(f) for f in normal_files} & {date_of(f) for f in icing_files})
    results = {
        "v1_as_published": scores(y, v1),
        "zero_power_rule": scores(y, zero_power),
        "v1_with_idle_readings_kept": scores(y_all, v1_all),
        "icing_readings": int(len(positives)),
        "icing_readings_with_power_exactly_zero": int((positives[:, 1] == 0).sum()),
        "icing_readings_status_codes": {str(int(k)): int(v) for k, v in zip(*np.unique(positives[:, 2], return_counts=True))},
        "negative_readings_in_alarm_share": round(float(v1[: len(negatives)].mean()), 3),
        "dates_in_both_folders": duplicated,
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
