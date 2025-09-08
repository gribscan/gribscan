import numpy as np
import xarray as xr
from scipy.special import roots_legendre


default_attrs = {
    "lat": {
        "long_name": "latitude",
        "units": "degrees_north",
        "standard_name": "latitude",
    },
    "lon": {
        "long_name": "longitude",
        "units": "degrees_east",
        "standard_name": "longitude",
    },
    "time": {
        "units": "seconds since 1970-01-01T00:00:00",
        "calendar": "proleptic_gregorian",
    },
}


class GribGrid:
    _subclasses = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._subclasses.append(cls)


class GaussianReduced(GribGrid):
    gridType = "reduced_gg"
    params = ["pl"]

    @classmethod
    def compute_coords(cls, pl):
        lons = np.concatenate([np.linspace(0, 360, nl, endpoint=False) for nl in pl])
        single_lats = np.rad2deg(-np.arcsin(roots_legendre(len(pl))[0]))
        lats = np.concatenate([[lat] * nl for nl, lat in zip(pl, single_lats)])

        return xr.Dataset(
            coords={
                "lat": (("value",), lats, default_attrs["lat"]),
                "lon": (("value",), lons, default_attrs["lon"]),
            }
        )


class GaussianRegular(GribGrid):
    gridType = "regular_gg"
    params = ["N"]

    @classmethod
    def compute_coords(cls, N):
        lats = np.rad2deg(-np.arcsin(roots_legendre(2 * N)[0]))
        lons = np.linspace(0, 360, 4 * N, endpoint=False)

        return xr.Dataset(
            coords={
                "lat": (("lat",), lats, default_attrs["lat"]),
                "lon": (("lon",), lons, default_attrs["lon"]),
            }
        )


class LatLonReduced(GribGrid):
    gridType = "reduced_ll"
    params = ["pl"]

    @classmethod
    def compute_coords(cls, pl):
        lons = np.concatenate([np.linspace(0, 360, nl, endpoint=False) for nl in pl])
        single_lats = np.linspace(90, -90, len(pl), endpoint=True)
        lats = np.concatenate([[lat] * nl for nl, lat in zip(pl, single_lats)])

        return xr.Dataset(
            coords={
                "lat": (("value",), lats, default_attrs["lat"]),
                "lon": (("value",), lons, default_attrs["lon"]),
            }
        )


class LatLonRegular(GribGrid):
    gridType = "regular_ll"
    params = [
        "Ni",
        "Nj",
        "latitudeOfFirstGridPointInDegrees",
        "longitudeOfFirstGridPointInDegrees",
        "iDirectionIncrementInDegrees",
        "jDirectionIncrementInDegrees",
        "iScansNegatively",
        "jScansPositively",
    ]

    @classmethod
    def compute_coords(cls, **kwargs):
        Ni = kwargs["Ni"]
        Nj = kwargs["Nj"]
        iInc = kwargs["iDirectionIncrementInDegrees"]
        jInc = kwargs["jDirectionIncrementInDegrees"]
        lonFirst = kwargs["longitudeOfFirstGridPointInDegrees"]
        latFirst = kwargs["latitudeOfFirstGridPointInDegrees"]

        iInc = -iInc if kwargs["iScansNegatively"] else iInc
        jInc = jInc if kwargs["jScansPositively"] else -jInc

        lons = (lonFirst + np.arange(Ni) * iInc + 180) % 360 - 180
        lats = latFirst + np.arange(Nj) * jInc

        return xr.Dataset(
            coords={
                "lat": (("lat",), lats, default_attrs["lat"]),
                "lon": (("lon",), lons, default_attrs["lon"]),
            }
        )


class HEALPix(GribGrid):
    gridType = "healpix"
    params = [
        "orderingConvention",
        "Nside",
    ]

    @classmethod
    def compute_coords(cls, orderingConvention, Nside):
        import healpy as hp

        lons, lats = hp.pix2ang(
            nside=Nside,
            ipix=np.arange(hp.nside2npix(Nside)),
            nest=orderingConvention == "nested",
            lonlat=True,
        )

        return xr.Dataset(
            coords={
                "lat": (("value",), lats, default_attrs["lat"]),
                "lon": (("value",), lons, default_attrs["lon"]),
            }
        )


class SphericalHarmonics(GribGrid):
    gridType = "sh"
    params = []

    @classmethod
    def compute_coords(cls):
        return {}


grids = {g.gridType: g for g in GribGrid._subclasses}


def params_for_gridType(gridType):
    if gridType in grids:
        return grids[gridType].params
    else:
        return []


def varinfo2coords(varinfo):
    grid = grids[varinfo["attrs"]["gridType"]]
    return grid.compute_coords(**{k: varinfo["extra"][k] for k in grid.params})
