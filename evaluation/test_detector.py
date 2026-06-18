"""
Unit tests for the icing detector and power curve.
No dataset required — tests core logic with known inputs.
Run in CI on every push.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.detector.power_curve import expected_power, power_ratio
from app.detector.icing_detector import IcingDetector

def test_expected_power_below_cutin():
    assert expected_power(1.0) == 0.0

def test_expected_power_above_cutoff():
    assert expected_power(15.0) == 0.0

def test_expected_power_normal():
    assert expected_power(3.0) > 0.0

def test_power_ratio_undefined_below_cutin():
    assert power_ratio(0.0, 1.0) is None

def test_power_ratio_zero_during_icing():
    ratio = power_ratio(0.0, 3.0)
    assert ratio is not None
    assert ratio < 0.1

def test_power_ratio_normal_operation():
    ratio = power_ratio(1.533, 3.0)
    assert ratio is not None
    assert 0.9 < ratio < 1.1

def test_detector_fires_on_icing():
    detector = IcingDetector()
    # Feed 10 readings with zero power at cut-in wind — should trigger
    for _ in range(10):
        result = detector.process(wind_speed=3.0, actual_power=0.0)
    assert result.is_icing is True

def test_detector_clear_on_normal():
    detector = IcingDetector()
    # Feed 10 readings with normal power — should not trigger
    for _ in range(10):
        result = detector.process(wind_speed=3.0, actual_power=1.5)
    assert result.is_icing is False

def test_detector_requires_window_fill():
    detector = IcingDetector()
    # Only 5 readings — window not full, should not fire
    for _ in range(5):
        result = detector.process(wind_speed=3.0, actual_power=0.0)
    assert result.is_icing is False

if __name__ == "__main__":
    tests = [
        test_expected_power_below_cutin,
        test_expected_power_above_cutoff,
        test_expected_power_normal,
        test_power_ratio_undefined_below_cutin,
        test_power_ratio_zero_during_icing,
        test_power_ratio_normal_operation,
        test_detector_fires_on_icing,
        test_detector_clear_on_normal,
        test_detector_requires_window_fill,
    ]
    passed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
