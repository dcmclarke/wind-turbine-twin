import json
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.feeds import mqtt as mqtt_feed


class FakeClient:
    """Stands in for the paho client; records which messages were acknowledged."""

    def __init__(self):
        self.acked = []

    def ack(self, mid, qos):
        self.acked.append(mid)


def message(mid: int, **overrides) -> SimpleNamespace:
    body = {"timestamp": "2022-12-17T16:00:00", "wind_mean": 3.0, "power_mean": 1.5} | overrides
    return SimpleNamespace(payload=json.dumps(body).encode(), mid=mid, qos=1)


@pytest.fixture
def feed():
    return mqtt_feed.MqttFeed(get_settings())


def test_acks_are_manual(feed):
    # paho has no public getter; without this, paho acks every message itself
    assert feed.client._manual_ack is True


def test_reading_is_acked_after_it_is_saved(client, feed):
    fake = FakeClient()
    feed._on_message(fake, None, message(1))
    assert fake.acked == [1]
    assert len(client.get("/api/readings").json()) == 1


def test_reading_is_not_acked_when_saving_fails(client, feed, monkeypatch):
    def database_down(*args, **kwargs):
        raise RuntimeError("database down")

    monkeypatch.setattr(mqtt_feed, "ingest", database_down)
    fake = FakeClient()
    feed._on_message(fake, None, message(1))
    assert fake.acked == []


def test_database_outage_is_waited_out_so_no_reading_is_skipped(client, feed, monkeypatch):
    """Moving on to the next reading would leave a gap: the failed one could only come back out of order."""
    from sqlalchemy.exc import OperationalError

    real_ingest = mqtt_feed.ingest
    calls = []

    def down_twice(*args, **kwargs):
        calls.append(1)
        if len(calls) <= 2:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        return real_ingest(*args, **kwargs)

    monkeypatch.setattr(mqtt_feed, "ingest", down_twice)
    monkeypatch.setattr(mqtt_feed, "DB_RETRY_SECONDS", 0)
    fake = FakeClient()
    feed._on_message(fake, None, message(1))
    assert len(calls) == 3
    assert fake.acked == [1]
    assert len(client.get("/api/readings").json()) == 1


def test_readings_that_can_never_be_stored_are_acked(client, feed):
    """Redelivering a duplicate, out-of-order or malformed reading would never succeed."""
    fake = FakeClient()
    feed._on_message(fake, None, message(1))
    feed._on_message(fake, None, message(2))                                  # duplicate
    feed._on_message(fake, None, message(3, timestamp="2022-12-17T15:00:00"))  # out of order
    feed._on_message(fake, None, message(4, wind_mean=-1))                    # malformed
    assert fake.acked == [1, 2, 3, 4]


def test_health_waits_for_the_mqtt_subscription(client, feed, monkeypatch):
    """Docker Compose starts the edge publisher once /health is OK, so it must mean 'subscribed'."""
    from app import feeds

    monkeypatch.setattr(feeds, "running", feed)
    assert client.get("/health").status_code == 503

    feed._on_subscribe(FakeClient(), None, 1, [], None)
    assert client.get("/health").status_code == 200
