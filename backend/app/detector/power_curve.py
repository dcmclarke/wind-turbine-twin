"""
AV-7 power curve — derived from normal operation SCADA data.

Bin means fitted from 873,656 readings (status=10, generating)
across 10 HDF5 files from the ETH Zurich Aventa AV-7 dataset.
See ingestion/explore.ipynb for the full derivation.

Physical parameters (ETH Zurich documentation):
  Rated power:    7.0 kW
  Cut-in speed:   2.0 m/s
  Cut-off speed:  14.0 m/s
  Rotor diameter: 12.8 m
  Max RPM:        63
"""

# Binned mean power curve: wind speed (m/s) -> expected power (kW)
# Derived from normal operation data, 0.5 m/s bins
POWER_CURVE = {
    2.0:  0.453,
    2.5:  0.871,
    3.0:  1.533,
    3.5:  2.323,
    4.0:  3.339,
    4.5:  4.426,
    5.0:  5.287,
    5.5:  5.902,
    6.0:  6.410,
    6.5:  6.673,
    7.0:  6.779,
    7.5:  6.870,
    8.0:  6.880,
    8.5:  6.874,
    9.0:  6.859,
    9.5:  6.848,
    10.0: 6.827,
    10.5: 6.864,
    11.0: 6.781,
    11.5: 6.656,
    12.0: 6.837,
    12.5: 6.849,
    13.0: 6.837,
    13.5: 6.832,
    14.0: 6.811,
}

CUT_IN  = 2.0   # m/s
CUT_OFF = 14.0  # m/s
RATED   = 7.0   # kW
BIN_SIZE = 0.5  # m/s


def expected_power(wind_speed: float) -> float:
    """
    Return expected power output in kW for a given wind speed.

    Below cut-in or above cut-off: returns 0.0.
    Otherwise: finds the nearest 0.5 m/s bin and returns
    the empirical mean power from normal operation data.

    Args:
        wind_speed: Wind speed in m/s

    Returns:
        Expected power in kW
    """
    if wind_speed < CUT_IN or wind_speed > CUT_OFF:
        return 0.0

    # Round to nearest 0.5 m/s bin
    bin_key = round(round(wind_speed / BIN_SIZE) * BIN_SIZE, 1)

    # Clamp to curve bounds
    bin_key = max(CUT_IN, min(CUT_OFF, bin_key))

    return POWER_CURVE.get(bin_key, 0.0)


def power_ratio(actual_power: float, wind_speed: float) -> float | None:
    """
    Calculate power ratio: actual / expected.

    Returns None when expected power is zero (below cut-in or
    above cut-off) — ratio is undefined when turbine should not
    be producing power.

    Args:
        actual_power: Measured power output in kW
        wind_speed:   Measured wind speed in m/s

    Returns:
        Power ratio (0.0 to ~1.0) or None if undefined
    """
    exp = expected_power(wind_speed)
    if exp == 0.0:
        return None
    return actual_power / exp
