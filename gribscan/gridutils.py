import numpy as np
from scipy.special import roots_legendre


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
        return {"lon": lons, "lat": lats}


class LatLonReduced(GribGrid):
    gridType = "reduced_ll"
    params = ["pl"]

    @classmethod
    def compute_coords(cls, pl):
        lons = np.concatenate([np.linspace(0, 360, nl, endpoint=False) for nl in pl])
        single_lats = np.linspace(90, -90, len(pl), endpoint=True)
        lats = np.concatenate([[lat] * nl for nl, lat in zip(pl, single_lats)])
        return {"lon": lons, "lat": lats}


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

        lons, lats = np.meshgrid(
            (lonFirst + np.arange(Ni) * iInc + 180) % 360 - 180,
            latFirst + np.arange(Nj) * jInc,
        )

        return {"lon": lons.ravel(), "lat": lats.ravel()}


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

        return {"lon": lons, "lat": lats}


grids = {g.gridType: g for g in GribGrid._subclasses}


def params_for_gridType(gridType):
    if gridType in grids:
        return grids[gridType].params
    else:
        return []


def varinfo2coords(varinfo):
    grid = grids[varinfo["attrs"]["gridType"]]
    return grid.compute_coords(**{k: varinfo["extra"][k] for k in grid.params})
