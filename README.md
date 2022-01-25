# gribscan

Tools to scan gribfiles and create zarr-compatible indices.

## warning

This repository is still experimental. The code is not yet tested for many kinds of files. It will likely not destroy your files, as it only accesses gribfiles in read-mode, but it may skip some information or may crash. Please file an issue if you discover something is missing.

## howto

### scanning gribs

`gribscan.py` scans a single gribfile for contained GRIB messages. Metadata about the contained messages as well as byte-locations of the contained GRIB messages are written in a [fsspec ReferenceFileSystem](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.implementations.reference.ReferenceFileSystem) compatible JSON file, which internally builds a [zarr](https://zarr.readthedocs.io/en/stable/index.html)-group structure.

```bash
python gribscan.py a.grib a.json
```

Alternatively, `gribscan` can also be called from Python to achieve the same result:

```python
import gribscan
gribscan.grib2kerchunk("a.grib", "a.json")
```

**Note:** While `gribscan` uses `cfgrib` partially to read GRIB metadata, it does so in a rather hacky way. That way, `gribscan` does not have to create temporary files and is much faster than `cfgrib` or [kerchunk.grib2](https://fsspec.github.io/kerchunk/reference.html#kerchunk.grib2.scan_grib), but it may not be as universal as `cfgrib` is. This is also the main reason for the warning above.

### reading indexed grib via zarr

The resulting JSON-file can be interpreted by `ReferenceFileSystem` and `zarr` as follows:

```python
import rawgribcodec
import xarray as xr
ds = xr.open_zarr("reference::a.json", consolidated=False)
ds
```

Note that `rawgribcodec` **must** be imported in order to register `rawgrib` as a [`numcodecs`](https://numcodecs.readthedocs.io/en/stable/index.html) codec, which enables the use of GRIB messages as zarr-chunks. As opposed to `gribscan`, `rawgribcodec` only depends on `eccodes` and doesn't use `cfgrib` at all.

`fsspec` supports [URL chaining](https://filesystem-spec.readthedocs.io/en/latest/features.html#url-chaining). The prefix `reference::` before the path signals to `fsspec`, that after loading the given path, an `ReferenceFileSystem` should be initialized with whatever is found in that path. In principle, it's well possible to use `ReferenceFileSystem` also across HTTP or wihin ZIP files or a combination thereof...

### combining multiple gribs into a larger dataset

As the generated JSON files are already in `ReferenceFileSystem` / `kerchunk` compatible format, we can just use the tools provided by [`kerchunk`](https://fsspec.github.io/kerchunk/index.html) to aggretate multiple index files into one larger file:

```python
import rawgribcodec
from kerchunk.combine import MultiZarrToZarr

mzz = MultiZarrToZarr(
    "some_folder/*.json",  # <- pattern which can be used to glob for all the index-JSON-files
    remote_protocol="file",
    xarray_open_kwargs={
        #"preprocess": drop_coords,
        "decode_cf": False,
        "mask_and_scale": False,
        "decode_times": False,
        "decode_timedelta": False,
        "use_cftime": False,
        "decode_coords": False
    },
    xarray_concat_args={
        "dim": "time",
    }
)

mzz.translate("mzz.json")  # <- write output
```

The generated multi-zarr-file can be used just as the individual files.

## notebooks

There are a few notebooks which experiment with these tools:

* [gribscan_test.ipynb](gribscan_test.ipynb) looks at the output of a single `gribscan` run
* [build_index.ipynb](build_index.ipynb) generates many JSON index files
* [build_multizarr.ipynb](build_multizarr.ipynb) combines the generated JSON files into one and looks at the result
