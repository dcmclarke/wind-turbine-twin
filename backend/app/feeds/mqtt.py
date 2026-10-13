"""
MQTT feed: subscribe to 10-minute SCADA summaries from the edge gateway.

QoS 1 means the broker delivers each message at least once, so the same
reading can arrive twice after a reconnect. Readings are unique by
timestamp, so a repeat is logged and ignored rather than stored again.

Each message is acknowledged only after its reading is saved (or when it
can never be saved: malformed, duplicate, out of order). A reading that
fails to save, say because the database is down, stays unacknowledged and
the broker redelivers it when the backend reconnects. Limitation: the
broker only redelivers on reconnect, so if a single reading fails while
later ones succeed, the redelivered copy arrives out of order and is
dropped. This protects against outages, not one-off failures.
"""

import logging

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from app.config import Settings
from app.database import SessionLocal
from app.schemas import ReadingIn
from app.services.ingest import DuplicateReading, OutOfOrderReading, ingest

log = logging.getLogger(__name__)


class MqttFeed:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.received = 0
        # A persistent session (clean_session=False) makes the broker queue QoS 1
        # messages while the backend is down and deliver them when it reconnects.
        # manual_ack: acknowledge in _on_message once saved, not when it returns.
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="icing-backend",
                                  clean_session=False, manual_ack=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self) -> None:
        s = self.settings
        log.info("Connecting to MQTT broker %s:%s, topic %s", s.mqtt_host, s.mqtt_port, s.mqtt_topic)
        self.client.connect_async(s.mqtt_host, s.mqtt_port)
        self.client.loop_start()  # network loop in a background thread; reconnects automatically

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connection refused: %s", reason_code)
            return
        client.subscribe(self.settings.mqtt_topic, qos=1)
        log.info("Subscribed to %s", self.settings.mqtt_topic)

    def _on_message(self, client, userdata, message):
        try:
            data = ReadingIn.model_validate_json(message.payload)
        except ValidationError as e:
            log.warning("Rejected malformed reading: %s", e.errors()[0]["msg"])
            client.ack(message.mid, message.qos)
            return

        try:
            with SessionLocal() as db:
                ingest(db, data, source="mqtt")
            self.received += 1
        except DuplicateReading:
            log.info("Duplicate reading %s ignored", data.timestamp)
        except OutOfOrderReading as e:
            log.warning("Out-of-order reading ignored: %s", e)
        except Exception:
            # Not acknowledged, so the broker keeps it and redelivers it
            log.exception("Failed to store reading %s", data.timestamp)
            return
        client.ack(message.mid, message.qos)
