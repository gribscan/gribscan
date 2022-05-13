import numpy as np
import numcodecs

class MagicianBase:
    def variable_hook(self, key, info):
        ...

    def globals_hook(self, global_attrs):
        return global_attrs

    def coords_hook(self, name, coords):
        return {}, coords, {}, [name], None

    def m2key(self, meta):
        return tuple(meta[key] for key in self.varkeys), tuple(meta[key] for key in self.dimkeys)

    def m2dataset(self, meta):
        return "atm3d" if meta["attrs"]["typeOfLevel"].startswith("generalVertical") else "atm2d"

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
            attrs = {'units': 'seconds since 1970-01-01T00:00:00',
                     'calendar': 'proleptic_gregorian'}
        else:
            attrs = {}
        return attrs, coords, {}, [name], None


def make_gaussian_reduced(pl):
    lons = np.concatenate([np.linspace(0, 360, nl) for nl in pl])
    single_lats = np.linspace(90, -90, len(pl), endpoint=False) - (2 * 180 / len(pl))
    lats = np.concatenate([[lat]*nl for nl, lat in zip(pl, single_lats)])
    return lons, lats


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
            },
        }

    def coords_hook(self, name, coords):
        dims = [name]
        attrs = {}
        compressor = numcodecs.Blosc("zstd")
        if "time" in name:
            attrs = {'units': 'seconds since 1970-01-01T00:00:00',
                     'calendar': 'proleptic_gregorian'}
        elif name == "lat":
            dims = ["value"]
            attrs = {'long_name': 'latitude',
                     'units': 'degrees_north',
                     'standard_name': 'latitude'}
        elif name == "lon":
            dims = ["value"]
            attrs = {'long_name': 'longitude',
                     'units': 'degrees_east',
                     'standard_name': 'longitude'}
        return attrs, coords, {}, dims, compressor

    def extra_coords(self, varinfo):
        v0 = next(iter(varinfo.values()))
        pl = v0["extra"]["pl"]
        lons, lats = make_gaussian_reduced(pl)
        return {"lon": lons, "lat": lats}


MAGICIANS = {
    "monsoon": Magician,
    "ifs": IFSMagician,
}
