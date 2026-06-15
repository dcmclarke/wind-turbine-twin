"""
Icing detector evaluation against AV-7 labeled fault data.

Ground truth labeling:
    NORMAL (0): Normal operation files (status=10, wind >= cut-in).
                Status=10 confirmed as "generating" from data exploration
                in ingestion/explore.ipynb. Non-December icing files
                (April, August, September, November) also labeled normal.
    ICING  (1): December 17-18 files, wind >= cut-in, zero power confirmed.
                December 19-20 excluded — wind below cut-in, ambiguous.

Known limitation:
    The persistence filter requires WINDOW_SIZE readings before firing.
    The first (WINDOW_SIZE - 1) readings of any icing sequence will be
    false negatives regardless of power ratio. This is a deterministic
    property of the algorithm, not a failure of the detector.
    Documented here and in README.md.

Output:
    evaluation/confusion_matrix.png  — visual confusion matrix
    evaluation/metrics.json          — precision, recall, f1, counts

Usage:
    python evaluate.py

CI usage:
    python evaluate.py --baseline evaluation/metrics_baseline.json
    Fails if metrics deviate from stored baseline.
"""

import sys
import json
import argparse
import numpy as np
from pathlib import Path
from datetime import timezone

import h5py
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for CI
import matplotlib.pyplot as plt
from sklearn.metrics import (
    confusion_matrix,
    ConfusionMatrixDisplay,
    precision_score,
    recall_score,
    f1_score,
)

# Add backend to path so we can import the detector directly
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.detector.icing_detector import IcingDetector
from app.detector.power_curve import CUT_IN

# ── Paths ─────────────────────────────────────────────────────────────────────

EVAL_DIR     = Path(__file__).parent
ICING_PATH   = Path(__file__).parent.parent / "data" / "aventa_rotor_icing"
NORMAL_PATH  = Path(__file__).parent.parent / "data" / "aventa_normal_operation_for_system_identification"

ICING_DATES  = {"17_12_2022", "18_12_2022"}   # confirmed icing event
EXCLUDE_DATES = {"19_12_2022", "20_12_2022"}  # wind below cut-in, ambiguous


# ── Data loading ──────────────────────────────────────────────────────────────

def load_readings(hdf5_path: Path) -> list[dict]:
    """
    Load all wind speed and power readings from one HDF5 file.
    Skips blocks missing WM channels. Filters sentinel values.
    """
    readings = []
    try:
        with h5py.File(hdf5_path, "r") as f:
            blocks = list(f["Aventa"].keys())
            for block in blocks:
                try:
                    wind  = f[f"Aventa/{block}/WM2/Value"][:].flatten()
                    power = f[f"Aventa/{block}/WM3/Value"][:].flatten()
                    status = f[f"Aventa/{block}/WM5/Value"][:].flatten()
                    n = len(wind)
                    for i in range(n):
                        if wind[i] < -999 or power[i] < -999:
                            continue
                        readings.append({
                            "wind_speed":   float(wind[i]),
                            "power_output": float(power[i]),
                            "status":       float(status[i]),
                        })
                except KeyError:
                    continue
    except Exception as e:
        print(f"  Warning: could not read {hdf5_path.name}: {e}")
    return readings


def load_normal_data() -> list[tuple[dict, int]]:
    """
    Load normal operation data with label 0.

    Sources:
    - Normal operation dataset (status=10, wind >= cut-in)
    - Non-December files from icing dataset (April, Aug, Sep, Nov)
    """
    labeled = []

    # From normal operation dataset
    normal_files = sorted(NORMAL_PATH.glob("*.hdf5"))
    print(f"Loading {len(normal_files)} normal operation files...")
    for f in normal_files:
        readings = load_readings(f)
        for r in readings:
            # Only include confirmed generating readings
            if r["status"] == 10 and r["wind_speed"] >= CUT_IN:
                labeled.append((r, 0))

    # From non-icing months in the icing dataset
    icing_files = sorted(ICING_PATH.glob("*.hdf5"))
    for f in icing_files:
        # Extract date portion from filename
        # e.g. Aventa_Taggenberg_17_12_2022.hdf5 -> "17_12_2022"
        parts = f.stem.split("_")
        date_str = "_".join(parts[-3:])
        if date_str not in ICING_DATES and date_str not in EXCLUDE_DATES:
            readings = load_readings(f)
            for r in readings:
                if r["wind_speed"] >= CUT_IN and r["power_output"] >= 0:
                    labeled.append((r, 0))

    print(f"  Normal readings loaded: {len(labeled)}")
    return labeled


def load_icing_data() -> list[tuple[dict, int]]:
    """
    Load December 17-18 icing event data with label 1.
    Only includes readings where wind is above cut-in.
    """
    labeled = []
    icing_files = sorted(ICING_PATH.glob("*.hdf5"))

    print(f"Loading icing event files (Dec 17-18)...")
    for f in icing_files:
        parts = f.stem.split("_")
        date_str = "_".join(parts[-3:])
        if date_str in ICING_DATES:
            readings = load_readings(f)
            for r in readings:
                if r["wind_speed"] >= CUT_IN:
                    labeled.append((r, 1))

    print(f"  Icing readings loaded: {len(labeled)}")
    return labeled


# ── Detector evaluation ───────────────────────────────────────────────────────

def run_detector(
    labeled_readings: list[tuple[dict, int]],
) -> tuple[list[int], list[int]]:
    """
    Feed labeled readings through a fresh IcingDetector instance.

    Returns:
        y_true: ground truth labels (0=normal, 1=icing)
        y_pred: detector predictions (0=no alert, 1=alert)
    """
    detector = IcingDetector()
    y_true = []
    y_pred = []

    for reading, label in labeled_readings:
        result = detector.process(
            wind_speed=reading["wind_speed"],
            actual_power=reading["power_output"],
        )
        y_true.append(label)
        y_pred.append(1 if result.is_icing else 0)

    return y_true, y_pred


# ── Metrics and output ────────────────────────────────────────────────────────

def compute_and_save_metrics(
    y_true: list[int],
    y_pred: list[int],
) -> dict:
    """
    Compute precision, recall, F1. Save confusion matrix PNG and metrics JSON.
    """
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall    = recall_score(y_true, y_pred, zero_division=0)
    f1        = f1_score(y_true, y_pred, zero_division=0)
    cm        = confusion_matrix(y_true, y_pred)

    print()
    print("=== Evaluation Results ===")
    print(f"  Total readings:  {len(y_true)}")
    print(f"  Normal (label 0): {y_true.count(0)}")
    print(f"  Icing  (label 1): {y_true.count(1)}")
    print()
    print(f"  Precision: {precision:.3f}  (of all alerts, how many were real icing?)")
    print(f"  Recall:    {recall:.3f}  (of all icing readings, how many were caught?)")
    print(f"  F1 score:  {f1:.3f}")
    print()
    print("  Confusion matrix:")
    print(f"    TN={cm[0,0]}  FP={cm[0,1]}")
    print(f"    FN={cm[1,0]}  TP={cm[1,1]}")
    print()
    print("  Note: first (WINDOW_SIZE-1) icing readings are deterministic")
    print("  false negatives due to persistence filter warmup.")

    # Save confusion matrix PNG
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=["Normal", "Icing"],
    )
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title(
        "AV-7 Icing Detector — Confusion Matrix\n"
        "IEA T19 power ratio method, persistence filter N=10 M=7"
    )
    plt.tight_layout()
    output_png = EVAL_DIR / "confusion_matrix.png"
    plt.savefig(output_png, dpi=150)
    plt.close()
    print(f"  Confusion matrix saved: {output_png}")

    # Save metrics JSON
    metrics = {
        "precision":       round(precision, 4),
        "recall":          round(recall, 4),
        "f1":              round(f1, 4),
        "total_readings":  len(y_true),
        "normal_readings": y_true.count(0),
        "icing_readings":  y_true.count(1),
        "TP": int(cm[1, 1]),
        "TN": int(cm[0, 0]),
        "FP": int(cm[0, 1]),
        "FN": int(cm[1, 0]),
    }
    output_json = EVAL_DIR / "metrics.json"
    with open(output_json, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Metrics saved:          {output_json}")

    return metrics


def compare_to_baseline(metrics: dict, baseline_path: Path) -> bool:
    """
    Compare current metrics to a stored baseline.
    Returns True if results are acceptable, False if CI should fail.

    We allow small floating point variance (±0.01) rather than
    exact equality, since dataset ordering could cause minor differences.
    """
    if not baseline_path.exists():
        print(f"\nNo baseline found at {baseline_path}")
        print("Run once without --baseline to generate it.")
        return True

    with open(baseline_path) as f:
        baseline = json.load(f)

    print("\n=== Baseline Comparison ===")
    passed = True
    for key in ["precision", "recall", "f1"]:
        current  = metrics[key]
        expected = baseline[key]
        diff     = abs(current - expected)
        status   = "OK" if diff <= 0.01 else "FAIL"
        if status == "FAIL":
            passed = False
        print(f"  {key:12s}: current={current:.4f}  baseline={expected:.4f}  diff={diff:.4f}  {status}")

    return passed


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate AV-7 icing detector against labeled data"
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Path to baseline metrics JSON for CI comparison",
    )
    args = parser.parse_args()

    print("=== AV-7 Icing Detector Evaluation ===")
    print()

    # Load data
    normal_data = load_normal_data()
    icing_data  = load_icing_data()

    # Evaluate normal and icing separately so the detector window
    # resets between datasets — this prevents normal operation
    # readings from warming up the window before icing data starts
    print("\nRunning detector on normal data...")
    y_true_n, y_pred_n = run_detector(normal_data)

    print("Running detector on icing data...")
    y_true_i, y_pred_i = run_detector(icing_data)

    # Combine results
    y_true = y_true_n + y_true_i
    y_pred = y_pred_n + y_pred_i

    # Compute metrics and save outputs
    metrics = compute_and_save_metrics(y_true, y_pred)

    # CI baseline comparison
    if args.baseline:
        passed = compare_to_baseline(metrics, Path(args.baseline))
        if not passed:
            print("\nCI FAILED: metrics deviate from baseline")
            sys.exit(1)
        else:
            print("\nCI PASSED")

    print("\nDone.")


if __name__ == "__main__":
    main()
