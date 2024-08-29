import itertools
import json
import base64
import pathlib
import uuid
from collections import defaultdict

import cfgrib
import eccodes
import numpy as np

from .magician import Magician
from . import gridutils as gu

import logging

logger = logging.getLogger("gribscan")


def find_stream(f, needle, buffersize=1024 * 1024):
    keep_going = True
    while keep_going:
        start = f.tell()
        buf = f.read(buffersize)
        if len(buf) < buffersize:
            keep_going = False
        try:
            idx = buf.index(needle)
        except ValueError:
            f.seek(-len(needle), 1)
            continue
        else:
            pos = start + idx
            f.seek(pos)
            return pos


def detect_large_grib1_special_coding(f, part_size):
    """
    This is from eccodes src/grib_io.c /* Special coding */ (couldn't find it in the specs...)
    """
    if part_size & 0x800000:  # this is a large grib, hacks are coming...
        start = f.tell()
        data = f.read(part_size)
        f.seek(start)
        assert data[7] == 1, "large grib mode only exists in Grib 1"

        s0len = 8
        s1start = s0len
        s1len = int.from_bytes(data[s1start : s1start + 3], "big")
        flags = data[s1start + 7]
        has_s2 = bool(flags & (1 << 7))
        has_s3 = bool(flags & (1 << 6))

        s2start = s1start + s1len
        if has_s2:
            s2len = int.from_bytes(data[s2start : s2start + 3], "big")
        else:
            s2len = 0

        s3start = s2start + s2len
        if has_s3:
            s3len = int.from_bytes(data[s3start : s3start + 3], "big")
        else:
            s3len = 0

        s4start = s3start + s3len

        s4len = int.from_bytes(data[s4start : s4start + 3], "big")
        if s4len < 120:
            return (part_size & 0x7FFFFF) * 120 - s4len + 4
        else:
            return part_size

    else:  # normal grib
        return part_size


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

    logger.debug(f"reading GRIB file with size {size}")

    while f.tell() < size:
        logger.debug(f"extract part {part + 1}")
        start = f.tell()
        indicator = f.peek(16)
        if indicator[:4] != b"GRIB":
            logger.info(f"non-consecutive messages, searching for part {part + 1}")
            start = find_stream(f, b"GRIB")
            indicator = f.peek(16)
        if len(indicator) < 16:
            indicator = f.read(16)
            f.seek(start)
        if len(indicator) < 16:
            logger.info(f"couldn't peek or seek indicator, assuming end of file at {start}")
            return

        grib_edition = indicator[7]

        if grib_edition == 1:
            part_size = int.from_bytes(indicator[4:7], "big")
            part_size = detect_large_grib1_special_coding(f, part_size)
        elif grib_edition == 2:
            part_size = int.from_bytes(indicator[8:16], "big")
        else:
            raise ValueError(f"unknown grib edition: {grib_edition}")

        data = f.read(part_size)
        if data[-4:] != b"7777":
            logger.warning(f"part {part + 1} is broken")
            f.seek(start + 1)
        else:
            yield start, part_size, grib_edition, data

        part += 1
        if skip and part > skip:
            break


EXTRA_PARAMETERS = [
    "forecastTime",
    "indicatorOfUnitOfTimeRange",
    "lengthOfTimeRange",
    "indicatorOfUnitForTimeRange",
    "productDefinitionTemplateNumber",
    "N",
    "timeRangeIndicator",
    "stepRange",
    "P1",
    "P2",
    "numberIncludedInAverage",
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
    1: 60 * 60,  # np.timedelta64(1, "h"),
    2: 24 * 60 * 60,  # np.timedelta64(1, "D"),
    # 3   Month
    # 4   Year
    # 5   Decade (10 years)
    # 6   Normal (30 years)
    # 7   Century (100 years)
    # 8-9 Reserved
    10: 3 * 60 * 60,  # np.timedelta64(3, "h"),
    11: 6 * 60 * 60,  # np.timedelta64(6, "h"),
    12: 12 * 60 * 60,  # np.timedelta64(12, "h"),
    13: 1,  # np.timedelta64(1, "s"),
    # 14-191  Reserved
    # 192-254 Reserved for local use
    # 255 Missing
}


def get_time_offset(gribmessage, lean_towards="end"):
    """Calculate time offset based on GRIB definition.

    See: https://codes.ecmwf.int/grib/format/grib1/ctable/5/

    For GRIB2 output, lean_towards now supports "start", "end" and "mid"
    - "start": use offset=0, timestamp is at the beginning of the period (mean over January 2020 is at 2020-01-01 00:00)
    - "end": use offset=<length_of_period>, timestamp is at the end of the period (mean over January 2020 is at 2020-02-01 00:00)
    - "mid": timestamp is *near* the center of the period, depending on its length:
      - annual: timestamp is on July 1st, 12:00 
      - monthly: timestamp is on the 15th, 12:00
      - daily: timestamp is at 12:00
      - sub-daily: timestamp is at the center of the period (e.g. 6-hourly means for the period 00:00-06:00 is at 03:00)
    """
    offset = 0  # np.timedelta64(0, "s")
    edition = int(gribmessage["editionNumber"])
    if edition == 1:
        timeRangeIndicator = int(gribmessage["timeRangeIndicator"])
        if timeRangeIndicator == 0:
            unit = time_range_units[
                int(gribmessage.get("indicatorOfUnitOfTimeRange", 255))
            ]
            offset += int(gribmessage["P1"]) * unit
        elif timeRangeIndicator == 1:
            pass
        elif timeRangeIndicator in [2, 3]:
            unit = time_range_units[
                int(gribmessage.get("indicatorOfUnitOfTimeRange", 255))
            ]
            if lean_towards == "start":
                offset += int(gribmessage["P1"]) * unit
            elif lean_towards == "end":
                offset += int(gribmessage["P2"]) * unit
        elif timeRangeIndicator == 4:
            unit = time_range_units[
                int(gribmessage.get("indicatorOfUnitOfTimeRange", 255))
            ]
            offset += int(gribmessage["P2"]) * unit
        elif timeRangeIndicator == 10:
            unit = time_range_units[
                int(gribmessage.get("indicatorOfUnitOfTimeRange", 255))
            ]
            offset += (int(gribmessage["P1"]) * 256 + int(gribmessage["P2"])) * unit
        elif timeRangeIndicator == 123:
            unit = time_range_units[
                int(gribmessage.get("indicatorOfUnitOfTimeRange", 255))
            ]
            if lean_towards == "end":
                N = int(gribmessage["numberIncludedInAverage"])
                offset += N * int(gribmessage["P2"]) * unit
        else:
            raise NotImplementedError(
                f"don't know how to handle timeRangeIndicator {timeRangeIndicator}"
            )
    else:
        try:
            options = production_template_numbers[
                int(gribmessage["productDefinitionTemplateNumber"])
            ]
        except KeyError:
            return offset
        if options["forcastTime"]:
            logger.info("forcastTime")
            unit = time_range_units[
                int(gribmessage.get("indicatorOfUnitOfTimeRange", 255))
            ]
            offset += gribmessage.get("forecastTime", 0) * unit

        if options["timeRange"]:
            logger.info("timeRange")
            if lean_towards == "start":
                logger.info("timeRange, lean to start")
                # do nothing, offset is already at the start
                offset += 0
            elif lean_towards == "end":
                logger.info("timeRange, lean to end")
                unit = time_range_units[
                    int(gribmessage.get("indicatorOfUnitOfTimeRange", 255))
                ]
                offset += gribmessage.get("lengthOfTimeRange", 0) * unit
            elif lean_towards == "mid":
                logger.info("timeRange, lean to mid")
                unit = time_range_units[
                    int(gribmessage.get("indicatorOfUnitOfTimeRange", 255))
                ]
                offseti = gribmessage.get("lengthOfTimeRange", 0) * unit
                offseti_h = offseti / 3600
                if offseti_h < 24:
                    logger.info('TimeRange: %.1f-hourly. Set time to middle of the interval by adding an offset of %.1f hours' % (offseti_h,offseti_h/2))
                    offset += int(3600 * offseti_h / 2)
                elif offseti_h == 24:
                    logger.info('TimeRange: daily. Set time to 12:00 by adding an offset of 12 hours')
                    offset += int(3600 * 12)
                elif int(offseti_h/24) in [28,29,30,31]:
                    logger.info('TimeRange: monthly. Set time to 12:00 at 15th of the month by adding an offset of 14.5 days')
                    offset += int(86400 * ( 14 + 1/2) )
                elif int(offseti_h/24) in [365,366]:
                    logger.info('TimeRange: annual. Set time to 12:00 at 1st of July by removing an offset of 183.5 days from the end of the interval')
                    offset += offseti - int(86400 * ( 183 + 1/2) )
                else:
                    raise ValueError(
                        'Trying to execute lean_towards="mid", but finding unexpected period length of %i hours. stepType: %s, step: %s, stepRange: %s' % (
                            offseti_h,gribmessage['stepType'],gribmessage['step'],gribmessage['stepRange']))
            else:
                raise ValueError('Unexpected option for lean_towards: %s' % lean_towards)
    return offset


def arrays_to_list(o):
    try:
        return o.tolist()
    except AttributeError:
        return o


def scan_gribfile(filelike, lean_towards='end', **kwargs):
    for offset, size, grib_edition, data in _split_file(filelike):
        mid = eccodes.codes_new_from_message(data)
        m = cfgrib.cfmessage.CfMessage(mid)
        t = eccodes.codes_get_native_type(m.codes_id, "values")
        s = eccodes.codes_get_size(m.codes_id, "values")

        global_attrs = {k: m[k] for k in cfgrib.dataset.GLOBAL_ATTRIBUTES_KEYS}
        for uuid_key in ["uuidOfHGrid", "uuidOfVGrid"]:
            try:
                global_attrs[uuid_key] = str(
                    uuid.UUID(eccodes.codes_get_string(mid, uuid_key))
                )
            except eccodes.KeyValueNotFoundError:
                pass

        yield {
            "globals": global_attrs,
            "attrs": {
                k: m.get(k, None)
                for k in cfgrib.dataset.DATA_ATTRIBUTES_KEYS
                + cfgrib.dataset.EXTRA_DATA_ATTRIBUTES_KEYS
            },
            "parameter_code": {
                k: m.get(k, None)
                for k in ["discipline", "parameterCategory", "parameterNumber"]
            },
            "posix_time": m["time"] + get_time_offset(m,lean_towards=lean_towards),
            "domain": m["globalDomain"],
            "member": m.get("number", None),
            "realization": m.get("realization", None),
            "time": f"{m['hour']:02d}{m['minute']:02d}",
            "date": f"{m['year']:04d}{m['month']:02d}{m['day']:02d}",
            "levtype": m.get("typeOfLevel", None),
            "level": m.get("level", None),
            "param": m.get("shortName", None),
            "type": m.get("dataType", None),
            "referenceTime": m["time"],
            "step": m["step"],
            "_offset": offset,
            "_length": size,
            "array": {
                "dtype": np.dtype(t).str,
                "shape": [s],
            },
            "extra": {
                k: arrays_to_list(m.get(k, None))
                for k in (EXTRA_PARAMETERS + gu.params_for_gridType(m["gridType"]))
            },
            **kwargs,
        }


def write_index(gribfile, idxfile=None, outdir=None, force=False, lean_towards='end'):
    p = pathlib.Path(gribfile)
    if outdir is None:
        outdir = p.parent

    if idxfile is None:
        idxfile = pathlib.Path(outdir) / (p.stem + ".index")

    if idxfile.exists() and not force:
        raise FileExistsError(f"Index file {idxfile} already exists!")

    # We need to use the gribfile (str) variable because Path() objects
    # collapse the "/./" notation used to denote subtrees.
    gen = scan_gribfile(open(p, "rb"), lean_towards=lean_towards, filename=gribfile)

    tempfile = idxfile.with_suffix(".index.partial")
    with open(tempfile, "w") as output_file:
        for record in gen:
            json.dump(record, output_file)
            output_file.write("\n")

    if force or not idxfile.exists():
        tempfile.rename(idxfile)
    else:
        logger.warning(f"Index file {idxfile} got created during runtime.")


def parse_index(indexfile, m2key, duplicate="replace"):
    index = {}
    with open(indexfile, "r") as f:
        for line in f:
            meta = json.loads(line)
            tinfo = m2key(meta)
            if tinfo in index:
                if duplicate == "replace":
                    index[tinfo] = meta
                elif duplicate == "keep":
                    continue
                elif duplicate == "error":
                    raise Exception(f"Duplicate message step: {tinfo}")
            else:
                index[tinfo] = meta
    return list(index.values())


def is_value(v):
    if v is None or v == "undef" or v == "unknown":
        return False
    else:
        return True


def inspect_grib_indices(messages, magician):
    coords_by_key = defaultdict(lambda: tuple(set() for _ in magician.dimkeys))
    size_by_key = defaultdict(set)
    attrs_by_key = {}
    extra_by_key = {}
    dtype_by_key = {}
    global_attrs = {}

    for msg in messages:
        varkey, coords = magician.m2key(msg)
        for existing, new in zip(coords_by_key[varkey], coords):
            existing.add(new)
        size_by_key[varkey].add(msg["array"]["shape"][0])
        attrs_by_key[varkey] = {k: v for k, v in msg["attrs"].items() if is_value(v)}
        extra_by_key[varkey] = {k: v for k, v in msg["extra"].items() if is_value(v)}
        dtype_by_key[varkey] = msg["array"]["dtype"]
        global_attrs = msg["globals"]

    for k, v in size_by_key.items():
        assert len(v) == 1, f"inconsistent shape of {k}"

    size_by_key = {k: list(v)[0] for k, v in size_by_key.items()}

    varinfo = {}
    for varkey, coords in coords_by_key.items():
        if all(len(c) == 1 for c in coords):
            dims = ()
            dim_id = ()
            shape = ()
        else:
            dims, dim_id, shape = map(
                tuple,
                zip(
                    *(
                        (dim, i, len(coords))
                        for i, (dim, coords) in enumerate(zip(magician.dimkeys, coords))
                        if len(coords) != 1
                    )
                ),
            )

        info = {
            "dims": dims,
            "shape": shape,
            "dim_id": dim_id,
            "coords": tuple(coords_by_key[varkey][i] for i in dim_id),
            "data_shape": [size_by_key[varkey]],
            "data_dims": ["cell"],
            "dtype": dtype_by_key[varkey],
            "attrs": attrs_by_key[varkey],
            "extra": extra_by_key[varkey],
        }
        varinfo[varkey] = {
            **info,
            **magician.variable_hook(varkey, info),
        }

    coords = defaultdict(set)
    for _, info in varinfo.items():
        for dim, cs in zip(info["dims"], info["coords"]):
            coords[dim] |= cs

    coords = {
        **{k: list(sorted(c)) for k, c in coords.items()},
        **magician.extra_coords(varinfo),
    }

    return global_attrs, coords, varinfo


def build_refs(messages, global_attrs, coords, varinfo, magician):
    coords_inv = {k: {v: i for i, v in enumerate(vs)} for k, vs in coords.items()}

    refs = {}
    for msg in messages:
        key, coord = magician.m2key(msg)
        info = varinfo[key]
        cs = [coord[d] for d in info["dim_id"]]
        chunk_id = ".".join(
            itertools.chain(
                map(str, [coords_inv[d][c] for d, c in zip(info["dims"], cs)]),
                ["0"] * len(info["data_dims"])
            )
        )
        refs[info["name"] + "/" + chunk_id] = [
            msg["filename"],
            msg["_offset"],
            msg["_length"],
        ]

    for varkey, info in varinfo.items():
        refs[info["name"] + "/.zattrs"] = json.dumps(
            {
                **info["attrs"],
                **info["extra"],
                "_ARRAY_DIMENSIONS": list(info["dims"]) + list(info["data_dims"]),
            }
        )
        shape = [len(coords[dim]) for dim in info["dims"]] + list(info["data_shape"])
        chunks = [1 for _ in info["shape"]] + list(info["data_shape"])
        refs[info["name"] + "/.zarray"] = json.dumps(
            {
                "shape": shape,
                "chunks": chunks,
                "compressor": {"id": "gribscan.rawgrib"},
                "dtype": info["dtype"],
                "fill_value": info["attrs"].get("missingValue", 9999),
                "filters": [],
                "order": "C",
                "zarr_format": 2,
            }
        )

    for name, cs in coords.items():
        cs = np.asarray(cs)
        attrs, cs, array_meta, dims, compressor = magician.coords_hook(name, cs)

        if compressor is None:
            compressor_id = None
            data = bytes(cs)
        else:
            compressor_id = compressor.get_config()
            data = bytes(compressor.encode(cs))

        refs[f"{name}/.zattrs"] = json.dumps({**attrs, "_ARRAY_DIMENSIONS": dims})
        refs[f"{name}/.zarray"] = json.dumps(
            {
                **{
                    "chunks": [cs.size],
                    "compressor": compressor_id,
                    "dtype": cs.dtype.str,
                    "fill_value": None,
                    "filters": [],
                    "order": "C",
                    "shape": [cs.size],
                    "zarr_format": 2,
                },
                **array_meta,
            }
        )
        refs[f"{name}/0"] = "base64:" + base64.b64encode(data).decode("ascii")

    refs[".zgroup"] = json.dumps({"zarr_format": 2})
    refs[".zattrs"] = json.dumps(magician.globals_hook(global_attrs))

    return refs


def is_zarr_key(key):
    return key.endswith((".zarray", ".zgroup", ".zattrs"))


def consolidate_metadata(refs):
    return json.dumps(
        {
            "zarr_consolidated_format": 1,
            "metadata": {
                key: json.loads(value)
                for key, value in refs.items()
                if is_zarr_key(key)
            },
        }
    )


def subtree(path, sep="/./"):
    """Return sub-tree of a given path.

    The start of a sub-tree is marked by a user-defined string (default '/./').

    Example:

    >>> subtree("/foo/bar/./baz/")
    "baz/"

    Notes:
        This funcion mimicks the behaviour of rsync in -R/--relative mode.
        https://askubuntu.com/a/552122
    """
    return path.split(sep)[-1]


def prepend_path(refs, prefix):
    """Prepend a path-prefix to all target filenames in a given reference filesystem.

    For absolute target paths, the existing target parents are overwritten.
    """
    return {
        k: [(pathlib.Path(prefix) / subtree(target[0])).as_posix()] + target[1:]
        if isinstance(target, list) else target
        for k, target in refs.items()
    }


def compress_extra_attributes(messages):
    it = iter(messages)
    mlast = next(it)
    yield mlast
    for m in it:
        if "extra" in m:
            lastextra = mlast["extra"]
            # if extra attribute in this message is large (i.e. a list or dict) and is the same as in previous message, replace it by a reference to the previous one
            extra = {
                k: lastextra[k]
                if k in lastextra and isinstance(v, (list, dict)) and lastextra[k] == v
                else v
                for k, v in m["extra"].items()
            }
            m = {**m, "extra": extra}
        yield m
        mlast = m


def grib_magic(filenames, magician=None, global_prefix=None):
    if magician is None:
        magician = Magician()

    messages = list(
        compress_extra_attributes(
            msg
            for filename in filenames
            for msg in parse_index(filename, magician.m2key)
        )
    )

    messages_by_dataset = defaultdict(list)
    for message in messages:
        messages_by_dataset[magician.m2dataset(message)].append(message)

    refs_by_dataset = {}
    for dataset, messages in messages_by_dataset.items():
        global_attrs, coords, varinfo = inspect_grib_indices(messages, magician)
        refs = build_refs(messages, global_attrs, coords, varinfo, magician)
        refs[".zmetadata"] = consolidate_metadata(refs)
        if global_prefix is None:
            refs_by_dataset[dataset] = refs
        else:
            refs_by_dataset[dataset] = prepend_path(refs, global_prefix)

    return refs_by_dataset
