import json
import base64
import pathlib
from collections import defaultdict

import cfgrib
import eccodes
import numpy as np

import logging

logger = logging.getLogger("gribscan")

def _split_file(f, skip=0):
    """
    splits a gribfile into individual messages
    """
    if hasattr(f, "size"):
        size = f.size
    else:
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)
    part = 0

    while f.tell() < size:
        logger.debug(f"extract part {part + 1}")
        start = f.tell()
        f.seek(12, 1)
        part_size = int.from_bytes(f.read(4), "big")
        f.seek(start)
        data = f.read(part_size)
        assert data[:4] == b"GRIB"
        assert data[-4:] == b"7777"
        yield start, part_size, data
        part += 1
        if skip and part > skip:
            break

EXTRA_PARAMETERS = [
    "forecastTime",
    "indicatorOfUnitOfTimeRange",
    "lengthOfTimeRange",
    "indicatorOfUnitForTimeRange",
    "productDefinitionTemplateNumber",
]

production_template_numbers = {
    0: {"forcastTime": True, "timeRange": False},
    1: {"forcastTime": True, "timeRange": False},
    2: {"forcastTime": True, "timeRange": False},
    3: {"forcastTime": True, "timeRange": False},
    4: {"forcastTime": True, "timeRange": False},
    5: {"forcastTime": True, "timeRange": False},
    6: {"forcastTime": True, "timeRange": False},
    7: {"forcastTime": True, "timeRange": False},
    15: {"forcastTime": True, "timeRange": False},
    32: {"forcastTime": True, "timeRange": False},
    33: {"forcastTime": True, "timeRange": False},
    40: {"forcastTime": True, "timeRange": False},
    41: {"forcastTime": True, "timeRange": False},
    44: {"forcastTime": True, "timeRange": False},
    45: {"forcastTime": True, "timeRange": False},
    48: {"forcastTime": True, "timeRange": False},
    51: {"forcastTime": True, "timeRange": False},
    53: {"forcastTime": True, "timeRange": False},
    54: {"forcastTime": True, "timeRange": False},
    55: {"forcastTime": True, "timeRange": False},
    56: {"forcastTime": True, "timeRange": False},
    57: {"forcastTime": True, "timeRange": False},
    58: {"forcastTime": True, "timeRange": False},
    60: {"forcastTime": True, "timeRange": False},
    1000: {"forcastTime": True, "timeRange": False},
    1002: {"forcastTime": True, "timeRange": False},
    1100: {"forcastTime": True, "timeRange": False},
    40033: {"forcastTime": True, "timeRange": False},
    40455: {"forcastTime": True, "timeRange": False},
    40456: {"forcastTime": True, "timeRange": False},

    20: {"forcastTime": False, "timeRange": False},
    30: {"forcastTime": False, "timeRange": False},
    31: {"forcastTime": False, "timeRange": False},
    254: {"forcastTime": False, "timeRange": False},
    311: {"forcastTime": False, "timeRange": False},
    2000: {"forcastTime": False, "timeRange": False},

    8: {"forcastTime": True, "timeRange": True},
    9: {"forcastTime": True, "timeRange": True},
    10: {"forcastTime": True, "timeRange": True},
    11: {"forcastTime": True, "timeRange": True},
    12: {"forcastTime": True, "timeRange": True},
    13: {"forcastTime": True, "timeRange": True},
    14: {"forcastTime": True, "timeRange": True},
    34: {"forcastTime": True, "timeRange": True},
    42: {"forcastTime": True, "timeRange": True},
    43: {"forcastTime": True, "timeRange": True},
    46: {"forcastTime": True, "timeRange": True},
    47: {"forcastTime": True, "timeRange": True},
    61: {"forcastTime": True, "timeRange": True},
    67: {"forcastTime": True, "timeRange": True},
    68: {"forcastTime": True, "timeRange": True},
    91: {"forcastTime": True, "timeRange": True},
    1001: {"forcastTime": True, "timeRange": True},
    1101: {"forcastTime": True, "timeRange": True},
    10034: {"forcastTime": True, "timeRange": True},
}

# according to http://www.cosmo-model.org/content/consortium/generalMeetings/general2014/wg6-pompa/grib2/grib/pdtemplate_4.41.htm
time_range_units = {
    0: 60,  # np.timedelta64(1, "m"),
    1: 60*60,  # np.timedelta64(1, "h"),
    2: 24*60*60,  # np.timedelta64(1, "D"),
    #3   Month
    #4   Year
    #5   Decade (10 years)
    #6   Normal (30 years)
    #7   Century (100 years)
    #8-9 Reserved
    10: 3*60*60,  # np.timedelta64(3, "h"),
    11: 6*60*60,  # np.timedelta64(6, "h"),
    12: 12*60*60,  # np.timedelta64(12, "h"),
    13: 1,  # np.timedelta64(1, "s"),
    #14-191  Reserved
    #192-254 Reserved for local use
    #255 Missing
}

def get_time_offset(gribmessage):
    offset = 0  # np.timedelta64(0, "s")
    try:
        options = production_template_numbers[int(gribmessage["productDefinitionTemplateNumber"])]
    except KeyError:
        return offset
    if options["forcastTime"]:
        unit = time_range_units[int(gribmessage.get("indicatorOfUnitOfTimeRange", 255))]
        offset += gribmessage.get("forecastTime", 0) * unit
    # TODO: handling of time ranges, see cdo: libcdi/src/gribapi_utilities.c: gribMakeTimeString
    return offset

def gribscan(filelike):
    for offset, size, data in _split_file(filelike):
        m = cfgrib.cfmessage.CfMessage(eccodes.codes_new_from_message(data))
        t = eccodes.codes_get_native_type(m.codes_id, "values")
        s = eccodes.codes_get_size(m.codes_id, "values")

        yield {"globals": {k: m[k] for k in cfgrib.dataset.GLOBAL_ATTRIBUTES_KEYS},
               "attrs": {k: m.get(k, None) for k in cfgrib.dataset.DATA_ATTRIBUTES_KEYS + cfgrib.dataset.EXTRA_DATA_ATTRIBUTES_KEYS},
               "time": m["time"] + get_time_offset(m),
               "referenceTime": m["time"],
               "step": m["step"],
               "offset": offset,
               "size": size,
               "array": {
                   "dtype": np.dtype(t).str,
                   "shape": [s],
                },
               "extra": {k: m.get(k, None) for k in EXTRA_PARAMETERS},
               }

def raise_duplicate_error(a, b, context):
    raise ValueError("duplicate timestep in var: {name}, time: {time}".format(**context))

def use_first(a, b, context):
    return a

def use_second(a, b, context):
    return b

def grib2kerchunk_refs(filelike, file_ref, on_duplicate=raise_duplicate_error):
    """
    scans a gribfile for messages and returns indexing data in kerchunk-json format
    """
    refs = {}
    array_meta = {}
    array_attrs = {}

    chunks_by_time = {}

    for msg in gribscan(filelike):
        name = msg["attrs"]["shortName"]
        
        if name not in chunks_by_time:
            chunks_by_time[name] = {}
            global_attrs = msg["globals"]
            refs[f"{name}/.zattrs"] = json.dumps({**{k: v for k, v in msg["attrs"].items()
                                                          if v is not None and v not in {"undef", "unknown"}},
                                                  "_ARRAY_DIMENSIONS": ["time", "values"]})
            array_attrs[name] = msg["attrs"]
            array_meta[name] = msg["array"]

        time = msg["time"]
        chunk = [file_ref, msg["offset"], msg["size"]]

        if time in chunks_by_time[name]:
            chunks_by_time[name][time] = on_duplicate(chunks_by_time[name][time], chunk, {"name": name, "time": time})
        else:
            chunks_by_time[name][time] = chunk

    times = np.unique([k for name, times in chunks_by_time.items() for k in times])

    for name, timechunks in chunks_by_time.items():
        for i, t in enumerate(times):
            if t in timechunks:
                refs[f"{name}/{i}.0"] = timechunks[t]

        meta = array_meta[name]
        refs[f"{name}/.zarray"] = json.dumps({"chunks": [1, *meta["shape"]],
                                              "compressor": {"id": "rawgrib"},
                                              "dtype": meta["dtype"],
                                              "fill_value": array_attrs[name].get("missingValue", 9999),
                                              "filters": [],
                                              "order": "C",
                                              "shape": [len(times), *meta["shape"]],
                                              "zarr_format": 2,
                                              })

    refs["time/.zattrs"] = json.dumps({**cfgrib.dataset.COORD_ATTRS["time"], "_ARRAY_DIMENSIONS": ["time"]})
    refs["time/.zarray"] = json.dumps({"chunks": [len(times)],
                                       "compressor": None,
                                       "dtype": times.dtype.str,
                                       "fill_value": 0,
                                       "filters": [],
                                       "order": "C",
                                       "shape": [len(times)],
                                       "zarr_format": 2,
                                       })
    refs["time/0"] = "base64:" + base64.b64encode(bytes(times)).decode("ascii")

    refs[".zgroup"] = json.dumps({"zarr_format": 2})
    refs[".zattrs"] = json.dumps(global_attrs)

    return refs

def grib2kerchunk(infile, outfile, duplicate_strategy=None):
    if duplicate_strategy == "first":
        on_duplicate = use_first
    elif duplicate_strategy == "second":
        on_duplicate = use_second
    else:
        on_duplicate = raise_duplicate_error

    with open(infile, "rb") as f:
        refs = grib2kerchunk_refs(f, "{{u}}", on_duplicate)

    res = {
        "version": 1,
        "templates": {
            "u": pathlib.Path(infile).resolve().as_posix(),
        },
        "refs": refs
    }

    with open(outfile, "w") as indexfile:
        json.dump(res, indexfile)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="source gribfile")
    parser.add_argument("target", help="target index file (JSON)")
    parser.add_argument("-d", "--on_duplicate", default=None, help="what to do on duplicate messages (one of first, second, None)")
    args = parser.parse_args()

    #gribfile = "/work/bd1154/highresmonsoon/experiments/luk1000/luk1000_atm2d_ml_20200618T000000Z.grb2"
    grib2kerchunk(args.source, args.target, args.on_duplicate)

if __name__ == "__main__":
    main()
