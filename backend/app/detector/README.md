# Detector

IEA Wind Task 19 icing detection on 10-minute SCADA data.

- `reference_curve.py` — clean-blade reference curve (P10/P50/P90 per wind-speed bin), fitted by `data_prep/fit_reference_curve.py`
- `reference_curve.json` — the fitted curve the service uses
- `t19.py` — per-sample flags, the Task 19 persistence rule (3 samples for classes A/C, 6 for B), energy lost, and serialisable detector state

The detector has no database or web code, so the evaluation, the tests and
the API all run exactly the same logic.
