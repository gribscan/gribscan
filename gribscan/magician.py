import numpy as np
import numcodecs

from .gridutils import varinfo2coords


class MagicianBase:
    def variable_hook(self, key, info):
        ...

    def globals_hook(self, global_attrs):
        return global_attrs

    def coords_hook(self, name, coords):
        return {}, coords, {}, [name], None

    def m2key(self, meta):
        return tuple(meta[key] for key in self.varkeys), tuple(
            meta[key] for key in self.dimkeys
        )

    def m2dataset(self, meta):
        return (
            "atm3d"
            if meta["attrs"]["typeOfLevel"].startswith("generalVertical")
            else "atm2d"
        )

    def extra_coords(self, varinfo):
        return {}


class Magician(MagicianBase):
    varkeys = "param", "levtype"
    dimkeys = "posix_time", "level"

    def globals_hook(self, global_attrs):
        history = global_attrs.get("history", "")
        if len(history) > 0 and not history.endswith("\n"):
            history = history + "\r\n"
        history += "🪄🧙‍♂️🔮 magic dataset assembly provided by gribscan.Magician\r\n"
        return {**global_attrs, "history": history}

    def variable_hook(self, key, info):
        param, levtype = key
        name = param
        dims = info["dims"]

        if levtype == "generalVertical":
            name = param + "half" if param == "zg" else param
            dims = tuple("halflevel" if dim == "level" else dim for dim in dims)
        if levtype == "generalVerticalLayer":
            dims = tuple("fulllevel" if dim == "level" else dim for dim in dims)
        dims = tuple("time" if dim == "posix_time" else dim for dim in dims)

        return {
            "dims": dims,
            "name": name,
        }

    def coords_hook(self, name, coords):
        if "time" in name:
            attrs = {
                "units": "seconds since 1970-01-01T00:00:00",
                "calendar": "proleptic_gregorian",
            }
        else:
            attrs = {}
        return attrs, coords, {}, [name], None


class IFSMagician(MagicianBase):
    varkeys = "param", "levtype"
    dimkeys = "posix_time", "level"

    def globals_hook(self, global_attrs):
        history = global_attrs.get("history", "")
        if len(history) > 0 and not history.endswith("\n"):
            history = history + "\r\n"
        history += "🪄🧙‍♂️🔮 magic dataset assembly provided by gribscan.IFSMagician\r\n"
        return {**global_attrs, "history": history}

    def variable_hook(self, key, info):
        param, levtype = key
        name = param
        dims = info["dims"]

        if levtype == "generalVertical":
            name = param + "half" if param == "zg" else param
            dims = tuple("halflevel" if dim == "level" else dim for dim in dims)
        if levtype == "generalVerticalLayer":
            dims = tuple("fulllevel" if dim == "level" else dim for dim in dims)
        dims = tuple("time" if dim == "posix_time" else dim for dim in dims)

        return {
            "dims": dims,
            "name": name,
            "data_dims": ["value"],
            "attrs": {
                **info["attrs"],
                "coordinates": "lon lat",
                "missingValue": 9999,
            },
        }

    def coords_hook(self, name, coords):
        dims = [name]
        attrs = {}
        compressor = numcodecs.Blosc("zstd")
        if "time" in name:
            attrs = {
                "units": "seconds since 1970-01-01T00:00:00",
                "calendar": "proleptic_gregorian",
            }
        elif name == "lat":
            dims = ["value"]
            attrs = {
                "long_name": "latitude",
                "units": "degrees_north",
                "standard_name": "latitude",
            }
        elif name == "lon":
            dims = ["value"]
            attrs = {
                "long_name": "longitude",
                "units": "degrees_east",
                "standard_name": "longitude",
            }
        return attrs, coords, {}, dims, compressor

    def extra_coords(self, varinfo):
        v0 = next(iter(varinfo.values()))
        return varinfo2coords(v0)

    def m2dataset(self, meta):
        return (
            "atm3d"
            if meta["attrs"]["typeOfLevel"].startswith("isobaricInhPa")
            else "atm2d"
        )

class IFSMagicianEERIE(IFSMagician):
    '''
    More differentiation on output files, for EERIE project
    - split stepType instant/accum/avg/min/max
    - make time-axis based on "referenceTime" not "posix_time" (assumes that time-axis in grib is NOT fc-type as initial_time + step)
        NOT consistent with previous catalogues. where e.g. mean over Jan 2020 is indexed as 2020-02-01
        NOW mean over Jan 2020 is indexed as 2020-01-01 (following convention of significanceOfReferenceTime=2)
        (TODO: maybe possible to instead put an automatic option into get_time_offset to e.g. set offset=0 if gribmessage.get("significanceOfReferenceTime")==2
    - makes ensemble "realization" axis (for "ed" class requires eccodes >= 2.36.1)
    '''

    # dimkeys = "referenceTime", "level", "realization"
    dimkeys = "posix_time", "level", "realization"

    def coords_hook(self, name, coords):
        dims = [name]
        attrs = {}
        compressor = numcodecs.Blosc("zstd")
        if "time" in name:
            attrs = {
                "units": "seconds since 1970-01-01T00:00:00",
                "calendar": "proleptic_gregorian",
            }
        elif name == "realization":
            # dims = ["value"]
            attrs = {
                "long_name": "realization",
                "units": "",
                "standard_name": "realization",
            }
        elif name == "lat":
            dims = ["value"]
            attrs = {
                "long_name": "latitude",
                "units": "degrees_north",
                "standard_name": "latitude",
            }
        elif name == "lon":
            dims = ["value"]
            attrs = {
                "long_name": "longitude",
                "units": "degrees_east",
                "standard_name": "longitude",
            }
        return attrs, coords, {}, dims, compressor
    
    def variable_hook(self, key, info):
        param, levtype = key
        name = param
        dims = info["dims"]

        if levtype == "generalVertical":
            name = param + "half" if param == "zg" else param
            dims = tuple("halflevel" if dim == "level" else dim for dim in dims)
        if levtype == "generalVerticalLayer":
            dims = tuple("fulllevel" if dim == "level" else dim for dim in dims)
        dims = tuple("time" if "time" in dim.lower() else dim for dim in dims)

        return {
            "dims": dims,
            "name": name,
            "data_dims": ["value"],
            "attrs": {
                **info["attrs"],
                "coordinates": "lon lat",
                "missingValue": 9999,
            },
        }
    
    def m2dataset(self, meta):
        # check for data dimensionality
        if meta["attrs"]["typeOfLevel"].startswith("isobaricInhPa"): # 3D field
            dim=3
        else:
            dim=2

        if meta['attrs']['stepType'] == 'instant': # instantaneous
            proc=""
        elif meta['attrs']['stepType'] == 'accum': # accumulations
            proc="_acc"
        elif meta['attrs']['stepType'] == 'avg': # time-averaged 
            proc="_avg"
        elif meta['attrs']['stepType'] == 'min': # min
            proc="_min"
        elif meta['attrs']['stepType'] == 'max': # max
            proc="_max"
        else:
            proc=""

        # constant fields (surface geopotential & lsm)
        if ( (meta['attrs']['paramId'] == 129) and (meta["level"] == 0) ) or (meta['attrs']['paramId'] == 172):
            dim=2
            proc="_const"
            
        # check for model grid
        if meta['attrs']['gridType'] == "reduced_ll": # reduced lat-lon grid (wave model native, pre 49r1)
            grid='_ll'
        else:
            grid=""

        outstr = 'atm%id%s%s' % (dim,grid,proc)
        return outstr

class IFSMagicianEERIE_v1(IFSMagician):
    '''
    first iteration of Magician for EERIE project, less functionality than IFSMagicianEERIE
    - Does NOT include time-axis based on "referenceTime"
        consistent with previous catalogues, putting TimeRange data as time_start + TimeRange, e.g. mean over Jan 2020 is indexed as 2020-02-01
    - Does NOT include realization-axis

    - DOES split stepType instant/accum/avg/min/max
    '''

    dimkeys = "posix_time", "level"

    def m2dataset(self, meta):
        # check for data dimensionality
        if meta["attrs"]["typeOfLevel"].startswith("isobaricInhPa"): # 3D field
            dim=3
        else:
            dim=2

        if meta['attrs']['stepType'] == 'instant': # instantaneous
            proc=""
        elif meta['attrs']['stepType'] == 'accum': # accumulations
            proc="_acc"
        elif meta['attrs']['stepType'] == 'avg': # time-averaged 
            proc="_avg"
        elif meta['attrs']['stepType'] == 'min': # min
            proc="_min"
        elif meta['attrs']['stepType'] == 'max': # max
            proc="_max"
        else:
            proc=""

        # constant fields (surface geopotential & lsm)
        if ( (meta['attrs']['paramId'] == 129) and (meta["level"] == 0) ) or (meta['attrs']['paramId'] == 172):
            dim=2
            proc="_const"
            
        # check for model grid
        if meta['attrs']['gridType'] == "reduced_ll": # reduced lat-lon grid (wave model native, pre 49r1)
            grid='_ll'
        else:
            grid=""

        outstr = 'atm%id%s%s' % (dim,grid,proc)
        return outstr
    
class EnsembleMagician(IFSMagician):
    varkeys = "param", "levtype"
    dimkeys = "posix_time", "level", "member"

    def m2dataset(self, meta):
        """Divide datasets based on the IFS ensemble products description.

        Reference:
          https://www.ecmwf.int/en/forecasts/datasets/open-data#ensemble-products
        """
        if meta["member"] is None:
            if meta["attrs"]["shortName"] in ("gh", "t", "ws", "msl"):
                return "ensmean"
            else:
                return "prob"
        if meta["attrs"]["typeOfLevel"].startswith("isobaricInhPa"):
            return "atm3d"
        return "atm2d"


MAGICIANS = {
    "monsoon": Magician,
    "ifs": IFSMagician,
    "ifseerie": IFSMagicianEERIE,
    "ifseeriev1": IFSMagicianEERIE_v1,
    "enfo": EnsembleMagician,
}
