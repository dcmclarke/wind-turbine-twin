from datetime import datetime, timedelta

START = datetime(2022, 12, 17, 16, 0, 0)
STEP = timedelta(seconds=601)
WIND = 3.0  # inside the reference range; expected power ~1.5 kW


def reading(i: int, power: float, wind: float = WIND) -> dict:
    return {"timestamp": (START + i * STEP).isoformat(), "wind_mean": wind, "power_mean": power}


def post(client, i, power, wind=WIND):
    return client.post("/api/readings", json=reading(i, power, wind))


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_reading_is_stored_with_detector_output(client):
    r = post(client, 0, power=1.5)
    assert r.status_code == 201
    body = r.json()
    assert body["flag"] == "normal"
    assert body["p10"] < body["p50"] < body["p90"]

    stored = client.get("/api/readings").json()
    assert [x["id"] for x in stored] == [body["id"]]


def test_stop_becomes_an_event_after_an_hour(client):
    for i in range(5):
        post(client, i, power=0.0)
    status = client.get("/api/status").json()
    assert status["active_event"] is None
    assert status["run"] == {"flag": "stopped", "length": 5, "required": 6}

    post(client, 5, power=0.0)
    status = client.get("/api/status").json()
    event = status["active_event"]
    assert event["event_class"] == "B"
    assert event["samples"] == 6
    assert event["started_at"] == reading(0, 0)["timestamp"]  # back-dated to the first stopped reading
    assert event["energy_lost_kwh"] > 0

    # Every reading of the run is linked to the event, including the five before it was confirmed
    readings = client.get("/api/readings").json()
    assert {r["event_id"] for r in readings} == {event["id"]}


def test_event_closes_when_power_returns(client):
    for i in range(6):
        post(client, i, power=0.0)
    post(client, 6, power=1.5)

    assert client.get("/api/status").json()["active_event"] is None
    events = client.get("/api/events").json()
    assert len(events) == 1
    assert events[0]["is_active"] is False
    assert events[0]["ended_at"] is not None


def test_state_survives_between_requests(client):
    """Each request uses a fresh session and detector; the run must carry over."""
    for i in range(3):
        post(client, i, power=0.0)
    assert client.get("/api/status").json()["run"]["length"] == 3


def test_duplicate_reading_is_rejected(client):
    post(client, 0, power=1.5)
    assert post(client, 0, power=1.5).status_code == 409
    assert len(client.get("/api/readings").json()) == 1


def test_out_of_order_reading_is_rejected(client):
    post(client, 5, power=1.5)
    assert post(client, 4, power=1.5).status_code == 422


def test_malformed_reading_is_rejected(client):
    r = client.post("/api/readings", json={"timestamp": "2022-12-17T16:00:00", "wind_mean": -3, "power_mean": 1})
    assert r.status_code == 422


def test_timezone_aware_timestamp_is_rejected(client):
    """Stored timestamps are naive turbine time; an aware one can't be compared with them."""
    for ts in ("2022-12-17T16:00:00+00:00", "2022-12-17T16:00:00Z"):
        r = client.post("/api/readings", json={"timestamp": ts, "wind_mean": WIND, "power_mean": 1.5})
        assert r.status_code == 422


def test_aware_timestamp_after_naive_one_is_rejected_not_a_crash(client):
    post(client, 0, power=1.5)
    aware = (START + STEP).isoformat() + "+00:00"
    r = client.post("/api/readings", json={"timestamp": aware, "wind_mean": WIND, "power_mean": 1.5})
    assert r.status_code == 422


def test_rejected_aware_reading_does_not_poison_detector_state(client):
    """An aware first reading used to be saved in the detector's state and break every later one."""
    aware = START.isoformat() + "+00:00"
    client.post("/api/readings", json={"timestamp": aware, "wind_mean": WIND, "power_mean": 1.5})
    assert post(client, 1, power=1.5).status_code == 201


def test_http_ingest_can_be_disabled(client, monkeypatch):
    from app.config import get_settings
    from app.routes import readings

    locked = get_settings().__class__(**{**get_settings().__dict__, "allow_http_ingest": False})
    monkeypatch.setattr(readings, "get_settings", lambda: locked)
    assert post(client, 0, power=1.5).status_code == 403


def test_reading_outside_reference_range_is_not_judged(client):
    body = post(client, 0, power=0.0, wind=9.0).json()
    assert body["flag"] == "no_reference"
    assert body["p50"] is None


def test_dashboard_bundles_everything(client):
    post(client, 0, power=1.5)
    body = client.get("/api/dashboard").json()
    assert set(body) == {"status", "readings", "events"}
    assert body["status"]["totals"]["readings"] == 1
    assert body["status"]["feed"]["mode"] == "none"


def test_reference_curve_endpoint(client):
    body = client.get("/api/reference-curve").json()
    assert len(body["bins"]) >= 3
    assert body["wind_range"][0] < body["wind_range"][1]
    assert body["stop_samples"] == 6
