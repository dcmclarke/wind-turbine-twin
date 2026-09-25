# Data preparation

Turns ETH Zurich's raw HDF5 files into the small files the rest of the project
uses. The outputs are committed, so this only needs rerunning if the method
changes. The raw download is described in [data/README.md](../data/README.md).

| File | What it does |
| :-- | :-- |
| `build_dataset.py` | Reads the ~7 Hz wind, power, RPM and status channels and writes one row of statistics per 10-minute block to `backend/app/data/av7_10min.csv` (916 rows). |
| `fit_reference_curve.py` | Fits the clean-blade P10/P50/P90 curve used by the running service to `backend/app/detector/reference_curve.json`. The evaluation refits its own curve for every held-out day. |
| `explore.ipynb` | The original exploration from version 1: channel mapping, the broken temperature sensor, status codes, and the raw-data power curve. Its threshold sweep and false-positive plots (`threshold_sweep.png`, `false_positive_wind_distribution.png`) belong to version 1's detector, which was replaced; see `evaluation/README.md`. |

Choices made while building the dataset:

- Five dates appear in both source folders as byte-identical files; each date is read once.
- Blocks that are missing the WM channels or shorter than 540 s are dropped: 10 of 926.
- RPM is the median, because about a fifth of RPM samples are spurious exact zeros while the rotor turns. Power has no such glitch.
- Dates 17–20 December 2022 are labelled `icing`, following the dataset's own README; the rest are `clean`.
