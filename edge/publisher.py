"""
Edge gateway simulator: publishes 10-minute SCADA summaries over MQTT.

On a real turbine, a small computer in the nacelle reads the controller's
signals, reduces them to 10-minute statistics and publishes those to the
site's MQTT broker. Sending one summary per 10 minutes instead of every
~7 Hz reading cuts the traffic by a factor of about 4,000, and 10-minute
statistics are what SCADA analysis (and the Task 19 method) works on anyway.

The statistics here were computed once from the raw ETH Zurich files by
data_prep/build_dataset.py, so this script replays them in time order.

Messages go out with QoS 1 (at-least-once): the broker acknowledges each
one, and the script waits for that before sending the next.

Usage:
    python edge/publisher.py --host localhost --seconds-per-sample 2
"""

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "backend" / "app" / "data" / "av7_10min.csv"
TURBINE_ID = "aventa-av7"


def to_message(row: dict) -> dict:
    def num(key: str) -> float | None:
        return float(row[key]) if row[key] != "" else None

    return {
        "turbine_id": TURBINE_ID,
        "timestamp": row["timestamp"],
        "wind_mean": float(row["wind_mean"]),
        "wind_std": num("wind_std"),
        "power_mean": float(row["power_mean"]),
        "rpm_median": num("rpm_median"),
        "status_mode": int(row["status_mode"]) if row["status_mode"] else None,
        # No temperature: the AV-7 sensor was broken for the whole dataset
    }


def main():
    parser = argparse.ArgumentParser(description="Publish AV-7 10-minute SCADA summaries over MQTT")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="windfarm/av7/scada/10min")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--seconds-per-sample", type=float, default=2.0,
                        help="wall-clock seconds between messages (2 = 300x real time)")
    parser.add_argument("--from", dest="start", default=None,
                        help="skip readings before this ISO timestamp, e.g. 2022-12-17T00:00")
    args = parser.parse_args()

    with open(args.csv, newline="") as f:
        rows = list(csv.DictReader(f))
    if args.start:
        start = datetime.fromisoformat(args.start)
        rows = [r for r in rows if datetime.fromisoformat(r["timestamp"]) >= start]

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"edge-{TURBINE_ID}")
    client.connect(args.host, args.port)
    client.loop_start()
    time.sleep(3)  # give the backend a moment to subscribe on a fresh start

    print(f"Publishing {len(rows)} readings to {args.topic} every {args.seconds_per_sample} s")
    for i, row in enumerate(rows, start=1):
        info = client.publish(args.topic, json.dumps(to_message(row)), qos=1)
        info.wait_for_publish()
        if i % 50 == 0 or i == len(rows):
            print(f"  {i}/{len(rows)}  {row['timestamp']}")
        time.sleep(args.seconds_per_sample)

    client.loop_stop()
    client.disconnect()
    print("Done.")


if __name__ == "__main__":
    main()
