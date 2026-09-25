import pytest

from app.detector.reference_curve import CurveBin, ReferenceCurve, percentile


def test_percentile_interpolates_like_numpy():
    values = [1.0, 2.0, 3.0, 4.0]
    assert percentile(values, 50) == pytest.approx(2.5)
    assert percentile(values, 10) == pytest.approx(1.3)
    assert percentile(values, 90) == pytest.approx(3.7)


def test_percentile_ignores_input_order():
    assert percentile([4.0, 1.0, 3.0, 2.0], 50) == pytest.approx(2.5)


def test_fit_drops_bins_with_too_few_samples():
    samples = [(3.0, 1.0)] * 10 + [(4.0, 2.0)] * 9
    curve = ReferenceCurve.fit(samples, bin_width=0.5, min_samples=10)
    assert [b.wind_speed for b in curve.bins] == [3.0]


def test_fit_records_percentiles_per_bin():
    samples = [(3.0, float(p)) for p in range(1, 12)]  # powers 1..11
    curve = ReferenceCurve.fit(samples, min_samples=10)
    b = curve.bins[0]
    assert (b.p10, b.p50, b.p90, b.samples) == (2.0, 6.0, 10.0, 11)


@pytest.fixture
def curve():
    return ReferenceCurve([
        CurveBin(wind_speed=3.0, p10=1.0, p50=2.0, p90=3.0, samples=20),
        CurveBin(wind_speed=4.0, p10=3.0, p50=4.0, p90=5.0, samples=20),
    ], bin_width=0.5)


def test_range_is_outer_bin_edges(curve):
    assert curve.wind_range == (2.75, 4.25)


def test_interpolates_between_bin_medians(curve):
    ref = curve.at(3.5)
    assert (ref.p10, ref.p50, ref.p90) == pytest.approx((2.0, 3.0, 4.0))


def test_holds_edge_value_between_edge_and_first_median(curve):
    assert curve.at(2.8).p50 == 2.0
    assert curve.at(4.2).p50 == 4.0


def test_refuses_to_extrapolate(curve):
    assert curve.at(2.7) is None
    assert curve.at(10.0) is None


def test_round_trips_through_dict(curve):
    restored = ReferenceCurve.from_dict(curve.to_dict())
    assert restored.bins == curve.bins
    assert restored.wind_range == curve.wind_range
