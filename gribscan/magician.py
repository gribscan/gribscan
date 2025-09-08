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
        return coords, {}, None


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
            "attrs": {
                **info["attrs"],
                "coordinates": "lon lat",
                "missingValue": 9999,
            },
        }

    def coords_hook(self, name, coords):
        compressor = numcodecs.Blosc("zstd")
        return coords, {}, compressor

    def m2dataset(self, meta):
        return (
            "atm3d"
            if meta["attrs"]["typeOfLevel"].startswith("isobaricInhPa")
            else "atm2d"
        )


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
    "enfo": EnsembleMagician,
}
