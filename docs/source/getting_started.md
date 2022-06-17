# getting started with gribscan

Tools to scan GRIB files and create zarr-compatible indices.

```{warning}
This repository is still experimental. The code is not yet tested for many kinds of files. It will likely not destroy your files, as it only accesses GRIB files in read-mode, but it may skip some information or may crash. Please file an issue if you discover something is missing.
```

## installing

`gribscan` is on [PyPI](http://pypi.org/project/gribscan/), you can install the recent released version using

```bash
python -m pip install gribscan
```

if you are interested in the recent development version, please clone the repository and install the package in development mode:

```bash
python -m pip install -e <path to your clone>
```

## command line usage

`gribscan` comes with two executables:

* `gribscan-index` for building indices of GRIB files
* `gribscan-build` for building a dataset from indices

### building indices

`gribscan` will create [jsonlines](https://jsonlines.org/)-based `.index`-files next to the input GRIB files. The format is based on the [ECMWF OpenData index format](https://confluence.ecmwf.int/display/UDOC/ECMWF+Open+Data+-+Real+Time#ECMWFOpenDataRealTime-IndexFilesIndexfiles) but contains a lot more entries.

You can pass in multiple GRIB files at once and specify the number of parallel processes (`-n`).

```bash
gribscan-index *.grb2 -n 16
```

**Note:** While `gribscan` uses `cfgrib` partially to read GRIB metadata, it does so in a rather hacky way. That way, `gribscan` does not have to create temporary files and is much faster than `cfgrib` or [kerchunk.grib2](https://fsspec.github.io/kerchunk/reference.html#kerchunk.grib2.scan_grib), but it may not be as universal as `cfgrib` is. This is also the main reason for the warning above.


### building a dataset

After all the index files have been created, a common dataset can be assembled based on the information in the index files. The assembled dataset will be written outin a [fsspec ReferenceFileSystem](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.implementations.reference.ReferenceFileSystem) compatible JSON file, which internally builds a [zarr](https://zarr.readthedocs.io/en/stable/index.html)-group structure.

```bash
gribscan-build *.index -o dataset.json --prefix <path prefix to referenced grib files>
```

The `prefix` will be prepended to the paths within the `dataset.json` and should point to the location of the original GRIB files.

## reading indexed grib via zarr

The resulting JSON-file can be interpreted by `ReferenceFileSystem` and `zarr` as follows:

```python
import gribscan
import xarray as xr
ds = xr.open_zarr("reference::dataset.json", consolidated=False)
ds
```

Note that `gribscan` **must** be imported in order to register `gribscan.rawgrib` as a [`numcodecs`](https://numcodecs.readthedocs.io/en/stable/index.html) codec, which enables the use of GRIB messages as zarr-chunks. As opposed to `gribscan-index`, the codec only depends on `eccodes` and doesn't use `cfgrib` at all.

`fsspec` supports [URL chaining](https://filesystem-spec.readthedocs.io/en/latest/features.html#url-chaining). The prefix `reference::` before the path signals to `fsspec`, that after loading the given path, an `ReferenceFileSystem` should be initialized with whatever is found in that path. In principle, it's well possible to use `ReferenceFileSystem` also across HTTP or wihin ZIP files or a combination thereof...


## library usage

You might be interested in using `gribscan` as a Python-library, which enables further usecases.

### building indices

You can build an index from a single GRIB file (as explained above) using:

```python
import gribscan
gribscan.write_index(gribfile, indexfile)
```

### building dataset references

You can also assemble a dataset from the incides using:

```python
import gribscan
magician = gribscan.Magician()
gribscan.grib_magic(indexfiles, magician, global_prefix)
```

The `magician` is a class which can customize how the dataset is assembled. You may want to define your own in order to design the resulting dataset according to your preferences. Please have a look at magician.py to see how a Magician would look like and check out the [magicians docs](magician.md).
