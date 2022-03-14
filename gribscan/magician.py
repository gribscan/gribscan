class MagicianBase:
    def variable_hook(self, key, info):
        ...

    def globals_hook(self, global_attrs):
        return global_attrs

    def coords_hook(self, name, coords):
        return {}, coords

    def m2key(self, meta):
        return tuple(meta[key] for key in self.varkeys), tuple(meta[key] for key in self.dimkeys)

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
        if len(dims) > 1:
            dims = tuple("time3D" if dim == "posix_time" else dim for dim in dims)
        else:
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
        return attrs, coords

