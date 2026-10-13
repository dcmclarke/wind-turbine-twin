"""
Reading sources. The running feed is kept here so /api/status can report
what is feeding the detector.
"""

from app.config import Settings
from app.schemas import FeedOut

running = None  # DemoFeed, MqttFeed or None


def start(settings: Settings) -> None:
    global running
    if settings.ingest_mode == "demo":
        from app.feeds.demo import DemoFeed
        running = DemoFeed(settings)
        running.start()
    elif settings.ingest_mode == "mqtt":
        from app.feeds.mqtt import MqttFeed
        running = MqttFeed(settings)
        running.start()


def stop() -> None:
    global running
    if running is not None:
        running.stop()
        running = None


def ready() -> bool:
    """False until the MQTT feed's subscription is confirmed; other feeds are ready at once."""
    return getattr(running, "subscribed", True)


def describe(settings: Settings) -> FeedOut:
    feed = FeedOut(mode=settings.ingest_mode)
    if settings.ingest_mode == "demo" and running is not None:
        feed.seconds_per_sample = running.interval
        feed.speedup = round(600 / running.interval)
        feed.loop = running.loop
        feed.position = running.position
        feed.total = running.total
    return feed
