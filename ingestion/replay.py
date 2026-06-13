"""
AV-7 SCADA data replay script.

Reads HDF5 files from the ETH Zurich Aventa AV-7 dataset and
replays them row by row to the FastAPI backend, simulating a
live sensor stream.

Timestamp reconstruction:
    HDF5 Time arrays are relative offsets in seconds from the
    block start time. Block names encode the time (e.g. "16_02_23"
    means 16:02:23). The file date comes from the filename
    (e.g. "Aventa_Taggenberg_17_12_2022.hdf5" = 2022-12-17).
    We combine these to build absolute UTC timestamps.

Usage:
    # Replay all icing files at full speed
    python replay.py --speed 0

    # Replay at real-time 1Hz
    python replay.py --speed 1

    # Replay only the December 17 icing event
    python replay.py --start 2022-12-17 --end 2022-12-18 --speed 0

    # Replay normal operation data
    python replay.py --dataset normal --speed 0
"""

import argparse
import time
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import h5py
import requests
import numpy as np

# ── Configuration ─────────────────────────────────────────────────────────────

API_URL = "http://localhost:8000/api/telemetry"

ICING_DATA_PATH = Path("C:/Projects/win-turbine-twin/data/aventa_rotor_icing/")
NORMAL_DATA_PATH = Path(
    "C:/Projects/win-turbine-twin/data/"
    "aventa_normal_operation_for_system_identification/"
)

# WM channels we care about
CHANNEL_MAP = {
    "rpm":          "WM1",  # rotor speed (RPM)
    "wind_speed":   "WM2",  # wind speed (m/s)
    "power_output": "WM3",  # power output (kW)
    "yaw_angle":    "WM4",  # yaw angle (deg)
    "rotor_status": "WM5",  # rotor status code
}


# ── Timestamp reconstruction ──────────────────────────────────────────────────

def parse_file_date(filename: str) -> datetime:
    """
    Extract the date from an AV-7 HDF5 filename.

    Example: "Aventa_Taggenberg_17_12_2022.hdf5" -> 2022-12-17
    The filename format is: Aventa_Taggenberg_DD_MM_YYYY.hdf5
    """
    # Split on underscore, last three parts are DD, MM, YYYY.hdf5
    parts = Path(filename).stem.split("_")
    day   = int(parts[-3])
    month = int(parts[-2])
    year  = int(parts[-1])
    return datetime(year, month, day, tzinfo=timezone.utc)


def parse_block_time(block_name: str) -> timedelta:
    """
    Extract time offset from a block name.

    Example: "16_02_23" -> timedelta(hours=16, minutes=2, seconds=23)
    Block names encode HH_MM_SS of the block start time.
    """
    parts = block_name.split("_")
    hours   = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2])
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def build_absolute_timestamp(
    file_date: datetime,
    block_offset: timedelta,
    reading_offset_seconds: float,
) -> datetime:
    """
    Combine file date, block start time, and per-reading offset
    into a single absolute UTC timestamp.

    Args:
        file_date:              Date from the filename (midnight UTC)
        block_offset:           Block start time as a timedelta
        reading_offset_seconds: Per-reading offset from the Time array

    Returns:
        Absolute UTC datetime for this specific reading
    """
    block_start = file_date + block_offset
    return block_start + timedelta(seconds=float(reading_offset_seconds))


# ── Data loading ──────────────────────────────────────────────────────────────

def load_block(f: h5py.File, block: str) -> list[dict]:
    """
    Load all SCADA readings from one 10-minute block.

    Returns a list of dicts, one per reading, with absolute
    timestamps already reconstructed.

    Returns empty list if the block is missing WM channels
    (some blocks use Channel_N naming instead).
    """
    try:
        # Read all WM channels for this block
        channels = {}
        for field, channel in CHANNEL_MAP.items():
            channels[field] = f[f"Aventa/{block}/{channel}/Value"][:].flatten()

        # Read the time offsets for this block
        # WM2 Time array is the reference — all WM channels share timing
        time_offsets = f[f"Aventa/{block}/WM2/Time"][:].flatten()

        # The WM Value arrays are shorter than the Time arrays
        # (Time is at 200Hz, Values are at ~7Hz SCADA rate)
        # We use the length of the Value array as our row count
        n_rows = len(channels["wind_speed"])

        # Build one reading per row
        readings = []
        for i in range(n_rows):
            # Filter out sentinel values (-1000000 means bad reading)
            wind = channels["wind_speed"][i]
            power = channels["power_output"][i]

            if wind < -999 or power < -999:
                continue

            # The Time array is 200Hz but Values are ~7Hz
            # Map reading index to the corresponding time offset
            # by scaling proportionally
            time_idx = int(i * len(time_offsets) / n_rows)
            time_offset = time_offsets[time_idx]

            readings.append({
                "wind_speed":   float(wind),
                "power_output": float(power),
                "rpm":          float(channels["rpm"][i]),
                "yaw_angle":    float(channels["yaw_angle"][i]),
                "rotor_status": float(channels["rotor_status"][i]),
                "time_offset":  float(time_offset),
            })

        return readings

    except KeyError:
        # Block uses Channel_N naming or is missing WM channels
        return []


# ── API communication ─────────────────────────────────────────────────────────

def post_reading(payload: dict) -> bool:
    """
    POST one SCADA reading to the API.

    Returns True on success, False on failure.
    Prints errors but doesn't crash — the replay continues
    even if individual readings fail.
    """
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        if response.status_code == 200:
            return True
        else:
            print(f"  API error {response.status_code}: {response.text[:100]}")
            return False
    except requests.ConnectionError:
        print("  Connection error — is the backend running? (docker compose up)")
        return False
    except requests.Timeout:
        print("  Request timed out")
        return False


# ── Main replay loop ──────────────────────────────────────────────────────────

def replay(
    data_path: Path,
    speed: float,
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    """
    Replay all HDF5 files in data_path chronologically.

    Args:
        data_path:  Path to folder containing HDF5 files
        speed:      Seconds to sleep between readings.
                    0 = as fast as possible
                    1 = real-time 1Hz
        start_date: Only replay readings on or after this date
        end_date:   Only replay readings before or on this date
    """
    # Find and sort HDF5 files chronologically by filename date
    hdf5_files = sorted(data_path.glob("*.hdf5"))

    if not hdf5_files:
        print(f"No HDF5 files found in {data_path}")
        sys.exit(1)

    print(f"Found {len(hdf5_files)} HDF5 files")
    print(f"Speed: {'real-time (1Hz)' if speed == 1 else 'maximum'}")
    if start_date:
        print(f"Start filter: {start_date.date()}")
    if end_date:
        print(f"End filter:   {end_date.date()}")
    print()

    total_sent = 0
    total_failed = 0

    for hdf5_path in hdf5_files:
        # Parse the date this file covers
        file_date = parse_file_date(hdf5_path.name)

        # Apply date filters
        if start_date and file_date.date() < start_date.date():
            continue
        if end_date and file_date.date() > end_date.date():
            continue

        print(f"── {hdf5_path.name} ({file_date.date()})")

        with h5py.File(hdf5_path, "r") as f:
            blocks = sorted(f["Aventa"].keys())

            for block in blocks:
                block_offset = parse_block_time(block)
                readings = load_block(f, block)

                if not readings:
                    continue

                for reading in readings:
                    # Build absolute timestamp for this reading
                    abs_timestamp = build_absolute_timestamp(
                        file_date,
                        block_offset,
                        reading["time_offset"],
                    )

                    # Build the API payload
                    payload = {
                        "timestamp":    abs_timestamp.isoformat(),
                        "wind_speed":   reading["wind_speed"],
                        "power_output": reading["power_output"],
                        "rpm":          reading["rpm"],
                        "yaw_angle":    reading["yaw_angle"],
                        "rotor_status": reading["rotor_status"],
                    }

                    # Send to API
                    success = post_reading(payload)
                    if success:
                        total_sent += 1
                        # Print progress every 100 readings
                        if total_sent % 100 == 0:
                            print(
                                f"  {abs_timestamp.isoformat()} | "
                                f"wind={reading['wind_speed']:.1f}m/s | "
                                f"power={reading['power_output']:.3f}kW | "
                                f"sent={total_sent}"
                            )
                    else:
                        total_failed += 1

                    # Throttle if real-time mode
                    if speed > 0:
                        time.sleep(speed)

    print()
    print(f"Replay complete. Sent: {total_sent}, Failed: {total_failed}")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Replay AV-7 SCADA data to the wind turbine digital twin API"
    )
    parser.add_argument(
        "--dataset",
        choices=["icing", "normal"],
        default="icing",
        help="Which dataset to replay (default: icing)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=0,
        help="Seconds between readings. 0=max speed, 1=real-time (default: 0)",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Only replay from this date. Format: YYYY-MM-DD",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="Only replay up to this date. Format: YYYY-MM-DD",
    )

    args = parser.parse_args()

    # Resolve data path
    data_path = ICING_DATA_PATH if args.dataset == "icing" else NORMAL_DATA_PATH

    # Parse date filters
    start_date = (
        datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.start else None
    )
    end_date = (
        datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.end else None
    )

    replay(data_path, args.speed, start_date, end_date)


if __name__ == "__main__":
    main()
