"""
MQTT feed: subscribe to 10-minute SCADA summaries from the edge gateway.

QoS 1 means the broker delivers each message at least once, so the same
reading can arrive twice after a reconnect. Readings are unique by
timestamp, so a repeat is logged and ignored rather than stored again.

Each message is acknowledged only after its reading is saved (or when it
can never be saved: malformed, duplicate, out of order). If the database
is unreachable, the same reading is retried until it is back. Moving on
would leave a gap: the broker only redelivers an unacknowledged message
after a reconnect, by which time newer readings would be stored and the
old one rejected as out of order. While a reading is retried no others
are read, so the broker keeps them queued, in order.

Any other failure (a bug, say) is logged and the message left
unacknowledged, so one bad reading can't stall the feed forever.
"""

import logging
import threading

import paho.mqtt.client as mqtt
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.database import SessionLocal
from app.schemas import ReadingIn
from app.services.ingest import DuplicateReading, OutOfOrderReading, ingest

log = logging.getLogger(__name__)

DB_RETRY_SECONDS = 5


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
        self.client.on_subscribe = self._on_subscribe
        self.client.on_message = self._on_message
        # Once the broker has confirmed the subscription it queues readings for
        # this session, even while the backend is down. Reported by /health.
        self.subscribed = False
        self._stopping = threading.Event()

    def start(self) -> None:
        s = self.settings
        log.info("Connecting to MQTT broker %s:%s, topic %s", s.mqtt_host, s.mqtt_port, s.mqtt_topic)
        self.client.connect_async(s.mqtt_host, s.mqtt_port)
        self.client.loop_start()  # network loop in a background thread; reconnects automatically

    def stop(self) -> None:
        self._stopping.set()  # ends a database retry, so the network thread can finish
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connection refused: %s", reason_code)
            return
        client.subscribe(self.settings.mqtt_topic, qos=1)

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        if any(rc.is_failure for rc in reason_code_list):
            log.error("MQTT subscription refused: %s", reason_code_list)
            return
        self.subscribed = True
        log.info("Subscribed to %s", self.settings.mqtt_topic)

    def _on_message(self, client, userdata, message):
        try:
            data = ReadingIn.model_validate_json(message.payload)
        except ValidationError as e:
            log.warning("Rejected malformed reading: %s", e.errors()[0]["msg"])
            client.ack(message.mid, message.qos)
            return

        try:
            if not self._store(data):
                return  # shutting down; the broker redelivers it next time
            self.received += 1
        except DuplicateReading:
            log.info("Duplicate reading %s ignored", data.timestamp)
        except OutOfOrderReading as e:
            log.warning("Out-of-order reading ignored: %s", e)
        except Exception:
            # Not acknowledged; the broker redelivers it after a reconnect
            log.exception("Failed to store reading %s", data.timestamp)
            return
        client.ack(message.mid, message.qos)

    def _store(self, data: ReadingIn) -> bool:
        """Save one reading, waiting out a database outage. False if stopped first."""
        while True:
            try:
                with SessionLocal() as db:
                    ingest(db, data, source="mqtt")
                return True
            except OperationalError:
                log.warning("Database unavailable; retrying reading %s in %s s", data.timestamp, DB_RETRY_SECONDS)
                if self._stopping.wait(DB_RETRY_SECONDS):
                    return False
