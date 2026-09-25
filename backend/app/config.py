"""
Settings, read once from environment variables (or a local .env file).

INGEST_MODE decides where 10-minute readings come from:
    demo  replay the bundled AV-7 dataset in a loop, in-process (default;
          used by the hosted demo, which has no MQTT broker)
    mqtt  subscribe to an MQTT broker; the edge publisher sends readings
    none  no automatic source; readings arrive only via POST /api/readings
"""

import os
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    database_url: str
    frontend_url: str | None
    ingest_mode: str
    allow_http_ingest: bool
    mqtt_host: str
    mqtt_port: int
    mqtt_topic: str
    demo_seconds_per_sample: float
    demo_live_from: datetime


@lru_cache
def get_settings() -> Settings:
    url = os.getenv("DATABASE_URL", "sqlite:///./local.db")
    # Name the driver explicitly (psycopg 3). Hosts hand out postgres:// or
    # postgresql:// URLs, and SQLAlchemy's default driver for those has changed
    # between versions.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]

    mode = os.getenv("INGEST_MODE", "demo").strip().lower()
    if mode not in ("demo", "mqtt", "none"):
        raise ValueError(f"INGEST_MODE must be demo, mqtt or none, not {mode!r}")

    return Settings(
        database_url=url,
        frontend_url=os.getenv("FRONTEND_URL") or None,
        ingest_mode=mode,
        allow_http_ingest=_bool("ALLOW_HTTP_INGEST"),
        mqtt_host=os.getenv("MQTT_HOST", "localhost"),
        mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
        mqtt_topic=os.getenv("MQTT_TOPIC", "windfarm/av7/scada/10min"),
        demo_seconds_per_sample=float(os.getenv("DEMO_SECONDS_PER_SAMPLE", "2")),
        # Readings before this are loaded instantly on each loop so a visitor
        # sees history at once; the rest streams live. Default: the last clean
        # day before the icing period, so ice shows up within a minute.
        demo_live_from=datetime.fromisoformat(os.getenv("DEMO_LIVE_FROM", "2022-11-04T00:00:00")),
    )
