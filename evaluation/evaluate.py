"""
Evaluation of the Task 19 icing detector on the AV-7 10-minute dataset.

Questions answered:
    1. Does the detector find the December 2022 icing event, and how quickly?
    2. How many false icing events does it raise on clean-blade days?
    3. Does it do better than a trivial rule that needs no power curve?

Method:
    Clean days are scored with leave-one-day-out cross-validation: for each
    clean day, the reference curve is fitted on the other clean days only,
    so no day is ever judged against a curve it helped build.
    The icing period (17-20 Dec 2022) is scored against a curve fitted on
    all clean days.

    The comparison rule ("zero-power baseline") raises an alarm for every
    10-minute sample with power below 1 % of rated and wind at or above the
    2 m/s cut-in. Consecutive alarms count as one event.

    Results are event-level first. With a single icing event in the public
    data, per-sample precision/recall would mostly measure how long that one
    event lasted, so sample-level figures are reported only as context.

Output:
    evaluation/results/metrics.json
    evaluation/results/reference_curve.png
    evaluation/results/icing_timeline.png

Usage:
    python evaluation/evaluate.py           # run and write results
    python evaluation/evaluate.py --check   # CI: fail if results differ from the committed metrics.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.dataset import Row, is_reference, load_rows  # noqa: E402
from app.detector.reference_curve import ReferenceCurve  # noqa: E402
from app.detector.t19 import EVENT_CLASS, Event, Flag, T19Config, detect  # noqa: E402

RESULTS_DIR = Path(__file__).parent / "results"
METRICS_PATH = RESULTS_DIR / "metrics.json"

CFG = T19Config()
CUT_IN = 2.0                       # m/s, AV-7 specification
SAMPLE = timedelta(minutes=10)
HOURS_PER_SAMPLE = SAMPLE.total_seconds() / 3600


# ── Helpers ───────────────────────────────────────────────────────────────────

def fit_curve(rows: list[Row]) -> ReferenceCurve:
    return ReferenceCurve.fit([(r.wind_mean, r.power_mean) for r in rows if is_reference(r)])


def samples_in_events(rows: list[Row], events: list[Event]) -> set[datetime]:
    """Timestamps of the samples covered by any event."""
    covered = set()
    for e in events:
        for r in rows:
            if e.started_at <= r.timestamp <= e.last_seen_at:
                covered.add(r.timestamp)
    return covered


def group_runs(timestamps: list[datetime]) -> list[list[datetime]]:
    """Group sorted alarm timestamps into runs of consecutive samples."""
    runs: list[list[datetime]] = []
    for ts in timestamps:
        if runs and (ts - runs[-1][-1]).total_seconds() <= CFG.max_gap_seconds:
            runs[-1].append(ts)
        else:
            runs.append([ts])
    return runs


def zero_power_alarms(rows: list[Row]) -> list[datetime]:
    return [
        r.timestamp for r in rows
        if r.wind_mean >= CUT_IN and r.power_mean < CFG.power_level * CFG.rated_power
    ]


# ── Clean days: leave-one-day-out ─────────────────────────────────────────────

def evaluate_clean_days(rows: list[Row]) -> dict:
    clean = [r for r in rows if r.period == "clean"]
    days = sorted({r.day for r in clean})

    false_events: list[dict] = []
    in_range = flagged = 0
    baseline_events = baseline_samples = 0
    by_day = {}

    for day in days:
        train = [r for r in clean if r.day != day]
        test = [r for r in clean if r.day == day]
        curve = fit_curve(train)

        results, events = detect([r.to_sample() for r in test], curve, CFG)
        judged = [r for r, res in zip(test, results) if res.flag != Flag.NO_REFERENCE]
        covered = samples_in_events(test, events)

        in_range += len(judged)
        flagged += len(covered)
        for e in events:
            false_events.append({
                "day": day,
                "class": e.event_class,
                "start": e.started_at.isoformat(),
                "samples": e.samples,
            })

        alarms = zero_power_alarms(test)
        baseline_samples += len(alarms)
        baseline_events += len(group_runs(alarms))
        by_day[day] = {"samples": len(test), "judged": len(judged), "false_events": len(events),
                       "baseline_false_events": len(group_runs(alarms))}

    judged_hours = in_range * HOURS_PER_SAMPLE
    above_cut_in = sum(1 for r in clean if r.wind_mean >= CUT_IN)
    return {
        "days": len(days),
        "samples": len(clean),
        "samples_judged": in_range,
        "hours_judged": round(judged_hours, 1),
        "false_events": len(false_events),
        "false_events_by_class": {c: sum(1 for e in false_events if e["class"] == c) for c in "ABC"},
        "false_events_per_24h_judged": round(len(false_events) / judged_hours * 24, 2) if judged_hours else None,
        "samples_in_false_events": flagged,
        "share_of_judged_samples_in_false_events": round(flagged / in_range, 3) if in_range else None,
        "false_event_list": false_events,
        "by_day": by_day,
        "baseline_zero_power": {
            "samples_above_cut_in": above_cut_in,
            "false_events": baseline_events,
            "false_alarm_samples": baseline_samples,
        },
    }


# ── Icing period ──────────────────────────────────────────────────────────────

def evaluate_icing(rows: list[Row], curve: ReferenceCurve) -> tuple[dict, list, list[Event]]:
    icing = [r for r in rows if r.period == "icing"]
    results, events = detect([r.to_sample() for r in icing], curve, CFG)

    judged = [r for r, res in zip(icing, results) if res.flag != Flag.NO_REFERENCE]
    covered = samples_in_events(icing, events)
    judged_covered = [r for r in judged if r.timestamp in covered]

    period_start = icing[0].timestamp
    confirmed_at = next((r.timestamp for r, res in zip(icing, results) if res.opened is not None), None)
    delay = (confirmed_at + SAMPLE - period_start) if confirmed_at else None

    alarms = zero_power_alarms(icing)
    baseline_runs = group_runs(alarms)
    baseline_delay = (alarms[0] + SAMPLE - period_start) if alarms else None

    metrics = {
        "period": [period_start.isoformat(), (icing[-1].timestamp + SAMPLE).isoformat()],
        "samples": len(icing),
        "samples_judged": len(judged),
        "detected": bool(events),
        "event_classes": sorted({e.event_class for e in events}),
        "events": len(events),
        "first_confirmed_at": (confirmed_at + SAMPLE).isoformat() if confirmed_at else None,
        "minutes_to_first_confirmation": round(delay.total_seconds() / 60) if delay else None,
        "judged_samples_inside_events": len(judged_covered),
        "share_of_judged_samples_inside_events": round(len(judged_covered) / len(judged), 3) if judged else None,
        "energy_lost_kwh": round(sum(e.energy_lost_kwh for e in events), 2),
        "event_list": [
            {"class": e.event_class, "start": e.started_at.isoformat(), "end": e.ended_at.isoformat() if e.ended_at else None,
             "samples": e.samples, "energy_lost_kwh": round(e.energy_lost_kwh, 2), "mean_wind": round(e.mean_wind, 2)}
            for e in events
        ],
        "baseline_zero_power": {
            "detected": bool(alarms),
            "events": len(baseline_runs),
            "alarm_samples": len(alarms),
            "minutes_to_first_alarm": round(baseline_delay.total_seconds() / 60) if baseline_delay else None,
        },
    }
    return metrics, results, events


# ── Figures ───────────────────────────────────────────────────────────────────

def draw_figures(rows: list[Row], curve: ReferenceCurve, icing_results: list, icing_events: list[Event]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    # Palette from the documented reference instance (validated: slots 1-2, all pairs)
    surface, ink, ink_2, muted, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
    blue, orange, critical = "#2a78d6", "#eb6834", "#d03b3b"

    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": ink_2,
        "xtick.color": muted, "ytick.color": muted, "axes.grid": True, "grid.color": grid,
        "grid.linewidth": 1, "grid.linestyle": "-", "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": surface, "axes.facecolor": surface, "legend.frameon": False,
    })

    # 1. Reference curve with clean and icing samples
    fig, ax = plt.subplots(figsize=(8, 4.8))
    low, high = curve.wind_range
    ax.axvspan(0, low, color=grid, alpha=0.5, lw=0)
    ax.axvspan(high, 8, color=grid, alpha=0.5, lw=0)
    ax.text(low / 2, 2.0, "no reference\ndata", ha="center", color=muted, fontsize=9)
    ax.text((high + 8) / 2, 2.0, "no reference data", ha="center", color=muted, fontsize=9)

    ref = [r for r in rows if is_reference(r)]
    ice = [r for r in rows if r.period == "icing"]
    ax.scatter([r.wind_mean for r in ref], [r.power_mean for r in ref], s=18, color=blue, alpha=0.55,
               edgecolors=surface, linewidths=1, label="Clean-blade samples (reference)")
    ax.scatter([r.wind_mean for r in ice], [r.power_mean for r in ice], s=18, color=orange, alpha=0.8,
               edgecolors=surface, linewidths=1, label="Icing period, 17–20 Dec 2022")

    xs = [low + (high - low) * i / 100 for i in range(101)]
    refs = [curve.at(x) for x in xs]
    ax.fill_between(xs, [r.p10 for r in refs], [r.p90 for r in refs], color=blue, alpha=0.12, lw=0, label="P10–P90 band")
    ax.plot(xs, [r.p50 for r in refs], color=ink, lw=2, label="Expected power (P50)")

    ax.set_xlim(0, 8)
    ax.set_ylim(-0.2, 6)
    ax.set_xlabel("10-minute mean wind speed (m/s)")
    ax.set_ylabel("10-minute mean power (kW)")
    ax.set_title("Reference power curve fitted from clean-blade data", loc="left", color=ink, fontsize=12)
    ax.legend(loc="upper right", fontsize=9, facecolor=surface, frameon=True, edgecolor=surface)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "reference_curve.png", dpi=150)
    plt.close(fig)

    # 2. Icing period timeline: wind (what the detector can judge) and power vs expected
    first_day = [r for r in ice if r.timestamp < ice[0].timestamp + timedelta(hours=32)]
    res = icing_results[:len(first_day)]
    t = [r.timestamp for r in first_day]

    fig, (ax_w, ax_p) = plt.subplots(2, 1, figsize=(9, 5.4), sharex=True, gridspec_kw={"height_ratios": [1, 1.4]})
    for ax in (ax_w, ax_p):
        for e in icing_events:
            if e.started_at <= t[-1]:
                ax.axvspan(e.started_at, min(e.ended_at or t[-1], t[-1] + SAMPLE), color=critical, alpha=0.10, lw=0)

    ax_w.axhspan(low, high, color=blue, alpha=0.08, lw=0)
    ax_w.text(t[-1], (low + high) / 2, "reference range ", ha="right", va="center", color=ink_2, fontsize=9)
    ax_w.plot(t, [r.wind_mean for r in first_day], color=blue, lw=2)
    ax_w.set_ylabel("Wind (m/s)")
    ax_w.set_title("17–18 Dec 2022: turbine stopped by ice while wind was in the operating range",
                   loc="left", color=ink, fontsize=12)

    exp_t = [ts for ts, rr in zip(t, res) if rr.reference is not None]
    exp_r = [rr.reference for rr in res if rr.reference is not None]
    ax_p.scatter(exp_t, [x.p50 for x in exp_r], s=16, color=ink, label="Expected power (P50) where judged", zorder=3)
    ax_p.plot(t, [r.power_mean for r in first_day], color=orange, lw=2, label="Actual power")
    ax_p.set_ylabel("Power (kW)")
    ax_p.set_ylim(-0.1, max(x.p50 for x in exp_r) * 1.25 if exp_r else 1)
    ax_p.text(icing_events[0].started_at, ax_p.get_ylim()[1] * 0.92, " icing events (class B, stopped)",
              color=ink_2, fontsize=9, va="top") if icing_events else None
    ax_p.legend(loc="upper right", fontsize=9)
    ax_p.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "icing_timeline.png", dpi=150)
    plt.close(fig)


# ── Entry point ───────────────────────────────────────────────────────────────

def run() -> tuple[dict, list[Row], ReferenceCurve, list, list[Event]]:
    rows = load_rows()
    curve = fit_curve(rows)
    icing_metrics, icing_results, icing_events = evaluate_icing(rows, curve)
    low, high = curve.wind_range

    metrics = {
        "dataset": {
            "samples": len(rows),
            "clean_samples": sum(r.period == "clean" for r in rows),
            "icing_samples": sum(r.period == "icing" for r in rows),
            "reference_samples": sum(is_reference(r) for r in rows),
        },
        "reference_curve": {"bins": len(curve.bins), "wind_range_ms": [round(low, 2), round(high, 2)]},
        "config": {"icing_samples": CFG.icing_samples, "stop_samples": CFG.stop_samples,
                   "temperature_condition": "not applied (sensor broken)"},
        "icing_period": icing_metrics,
        "clean_days": evaluate_clean_days(rows),
    }
    return metrics, rows, curve, icing_results, icing_events


def summarise(m: dict) -> None:
    ice, clean = m["icing_period"], m["clean_days"]
    print("=== Icing period (17-20 Dec 2022) ===")
    print(f"  detected: {ice['detected']}  classes: {ice['event_classes']}  events: {ice['events']}")
    print(f"  first event confirmed {ice['minutes_to_first_confirmation']} min after the period starts")
    print(f"  {ice['judged_samples_inside_events']} of {ice['samples_judged']} judged samples inside an event "
          f"({ice['samples'] - ice['samples_judged']} samples outside the reference range)")
    print(f"  energy lost: {ice['energy_lost_kwh']} kWh")
    print(f"  zero-power baseline: {ice['baseline_zero_power']}")
    print("=== Clean days (leave-one-day-out) ===")
    print(f"  {clean['false_events']} false events {clean['false_events_by_class']} in {clean['hours_judged']} judged hours "
          f"-> {clean['false_events_per_24h_judged']} per 24 h")
    print(f"  zero-power baseline: {clean['baseline_zero_power']['false_events']} false events")
    for day, d in clean["by_day"].items():
        print(f"    {day}: {d}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate the Task 19 icing detector")
    parser.add_argument("--check", action="store_true", help="fail if results differ from the committed metrics.json")
    args = parser.parse_args()

    metrics, rows, curve, icing_results, icing_events = run()
    summarise(metrics)

    if args.check:
        committed = json.loads(METRICS_PATH.read_text())
        if committed != json.loads(json.dumps(metrics)):
            print("\nFAIL: results differ from evaluation/results/metrics.json.")
            print("If the change is intended, run `python evaluation/evaluate.py` and commit the new results.")
            sys.exit(1)
        print("\nOK: results match evaluation/results/metrics.json")
        return

    RESULTS_DIR.mkdir(exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n")
    draw_figures(rows, curve, icing_results, icing_events)
    print(f"\nWrote {METRICS_PATH.relative_to(Path.cwd()) if METRICS_PATH.is_relative_to(Path.cwd()) else METRICS_PATH}")


if __name__ == "__main__":
    main()
