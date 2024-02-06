[![Documentation Status](https://readthedocs.org/projects/gribscan/badge/?version=latest)](https://gribscan.readthedocs.io/en/latest/?badge=latest) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10625188.svg)](https://doi.org/10.5281/zenodo.10625188)

# gribscan

Tools to scan GRIB files and create zarr-compatible indices.

## warning

This repository is still experimental. The code is not yet tested for many kinds of files. It will likely not destroy your files, as it only accesses GRIB files in read-mode, but it may skip some information or may crash. Please file an issue if you discover something is missing.

## installing

`gribscan` is on [PyPI](http://pypi.org/project/gribscan/), you can install the recent released version using

```bash
python -m pip install gribscan
```

if you are interested in the recent development version, please clone the repository and install the package in development mode:

```bash
python -m pip install -e <path to your clone>
```

## docs

The latest documentation can be found [online](https://gribscan.readthedocs.io) or may be built using sphinx in your local clone:

```bash
pip install -e .[docs]
cd docs
make html
```

afterwards, the documentation is available at `docs/build/html/index.html`.
