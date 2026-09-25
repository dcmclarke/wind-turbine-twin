import json
from datetime import datetime, timedelta

import pytest

from app.detector.reference_curve import CurveBin, ReferenceCurve
from app.detector.t19 import DetectorState, Flag, IcingDetector, Sample, T19Config, classify, detect

START = datetime(2022, 12, 17, 16, 0)
STEP = timedelta(seconds=601)  # AV-7 blocks are 601 s apart


@pytest.fixture
def curve():
    # Flat reference between 2.75 and 4.25 m/s: P10=2, P50=3, P90=4 kW
    return ReferenceCurve([
        CurveBin(wind_speed=3.0, p10=2.0, p50=3.0, p90=4.0, samples=20),
        CurveBin(wind_speed=4.0, p10=2.0, p50=3.0, p90=4.0, samples=20),
    ], bin_width=0.5)


def series(*powers, wind=3.5, start=START):
    return [Sample(start + i * STEP, wind, p) for i, p in enumerate(powers)]


NORMAL, LOW, STOP, HIGH = 3.0, 1.0, 0.0, 5.0


# ── Classification ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("power, flag", [
    (NORMAL, Flag.NORMAL),
    (LOW, Flag.UNDERPRODUCTION),
    (STOP, Flag.STOPPED),
    (HIGH, Flag.OVERPRODUCTION),
])
def test_classifies_against_the_reference(curve, power, flag):
    assert classify(Sample(START, 3.5, power), curve, T19Config())[0] == flag


def test_no_reference_outside_the_curve(curve):
    assert classify(Sample(START, 8.0, 0.0), curve, T19Config())[0] == Flag.NO_REFERENCE


def test_temperature_above_limit_rules_out_icing(curve):
    assert classify(Sample(START, 3.5, STOP, temperature=5.0), curve, T19Config())[0] == Flag.TOO_WARM


def test_temperature_below_limit_allows_icing(curve):
    assert classify(Sample(START, 3.5, STOP, temperature=-2.0), curve, T19Config())[0] == Flag.STOPPED


# ── Persistence rule ──────────────────────────────────────────────────────────

def test_underproduction_needs_three_samples_in_a_row(curve):
    _, events = detect(series(LOW, LOW), curve)
    assert events == []

    results, events = detect(series(LOW, LOW, LOW), curve)
    assert len(events) == 1
    assert results[2].opened is events[0]
    assert events[0].event_class == "A"
    assert events[0].started_at == START        # back-dated to the first sample
    assert events[0].samples == 3


def test_stop_needs_six_samples_in_a_row(curve):
    _, events = detect(series(*[STOP] * 5), curve)
    assert events == []

    _, events = detect(series(*[STOP] * 6), curve)
    assert [e.event_class for e in events] == ["B"]


def test_one_normal_sample_breaks_the_run(curve):
    _, events = detect(series(LOW, LOW, NORMAL, LOW, LOW), curve)
    assert events == []


def test_a_different_flag_starts_a_new_run(curve):
    results, events = detect(series(LOW, LOW, HIGH), curve)
    assert events == []
    assert results[-1].run_flag == Flag.OVERPRODUCTION
    assert results[-1].run_length == 1


def test_event_ends_at_first_sample_without_its_flag(curve):
    results, events = detect(series(LOW, LOW, LOW, LOW, NORMAL), curve)
    event = events[0]
    assert results[-1].closed is event
    assert event.samples == 4
    assert event.ended_at == event.last_seen_at + timedelta(minutes=10)
    assert results[-1].active is None


def test_gap_in_data_breaks_the_run(curve):
    before = series(LOW, LOW)
    after = series(LOW, start=before[-1].timestamp + timedelta(hours=1))
    _, events = detect(before + after, curve)
    assert events == []


def test_gap_in_data_ends_the_event(curve):
    before = series(LOW, LOW, LOW)
    after = series(NORMAL, start=before[-1].timestamp + timedelta(hours=1))
    results, events = detect(before + after, curve)
    assert results[-1].closed is events[0]


def test_energy_lost_is_shortfall_against_p50(curve):
    _, events = detect(series(*[STOP] * 6), curve)
    # 3 kW expected, 0 produced, six 10-minute samples = 3 kWh
    assert events[0].energy_lost_kwh == pytest.approx(3.0)


def test_overproduction_has_no_energy_loss(curve):
    _, events = detect(series(HIGH, HIGH, HIGH), curve)
    assert events[0].event_class == "C"
    assert events[0].energy_lost_kwh == 0.0


def test_rejects_samples_out_of_order(curve):
    detector = IcingDetector(curve)
    detector.process(Sample(START, 3.5, NORMAL))
    with pytest.raises(ValueError):
        detector.process(Sample(START, 3.5, NORMAL))


# ── Restart safety ────────────────────────────────────────────────────────────

def test_saved_state_resumes_exactly_where_it_left_off(curve):
    """
    Regression test for the original bug: the rolling window lived only in
    memory, so every restart of the hosted backend forgot an ongoing event.
    """
    samples = series(LOW, LOW, LOW, LOW, STOP, STOP, NORMAL, LOW, LOW)

    uninterrupted = IcingDetector(curve)
    expected = [uninterrupted.process(s) for s in samples]

    first = IcingDetector(curve)
    for s in samples[:4]:
        first.process(s)
    saved = json.loads(json.dumps(first.state.to_dict()))   # as stored in the database

    resumed = IcingDetector(curve, state=DetectorState.from_dict(saved))
    actual = [resumed.process(s) for s in samples[4:]]

    for got, want in zip(actual, expected[4:]):
        assert got.flag == want.flag
        assert got.run_length == want.run_length
        assert (got.closed is None) == (want.closed is None)
        if got.closed:
            assert got.closed.started_at == want.closed.started_at
            assert got.closed.samples == want.closed.samples
