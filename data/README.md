# Raw dataset (optional)

You only need this folder to rebuild the 10-minute dataset from scratch or to
rerun `evaluation/legacy_comparison.py`. Everything else — the tests, the
evaluation, the demo — runs on the 10-minute file already committed at
`backend/app/data/av7_10min.csv`.

The raw data is the ETH Zurich Aventa AV-7 research turbine dataset on Zenodo:
https://doi.org/10.5281/zenodo.8223010 (CC BY 4.0).

That page hosts four zip files for different experiments. Only two are used:

- `aventa_normal_operation_for_system_identification.zip` (6.8 GB)
- `aventa_rotor_icing.zip` (7.7 GB)

Extract them so the `.hdf5` files end up here:

```
data/
├── aventa_normal_operation_for_system_identification/
└── aventa_rotor_icing/
```

Five dates appear in both folders as byte-identical files; the build script
reads each date once.

Then rebuild the derived files:

```sh
python data_prep/build_dataset.py        # HDF5 -> backend/app/data/av7_10min.csv
python data_prep/fit_reference_curve.py  # -> backend/app/detector/reference_curve.json
```
