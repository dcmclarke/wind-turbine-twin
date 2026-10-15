from app.config import get_settings


def test_ingest_mode_defaults_to_none(monkeypatch):
    """Demo mode deletes every reading at the start of each loop, so it must be asked for."""
    monkeypatch.delenv("INGEST_MODE", raising=False)
    get_settings.cache_clear()
    try:
        assert get_settings().ingest_mode == "none"
    finally:
        get_settings.cache_clear()
