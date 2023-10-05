import numpy as np
from scipy.special import roots_legendre
from .rotated_grid import rot_to_reg


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


class LatLonRotated(GribGrid):
    gridType = "rotated_ll"
    params = [
        "Ni",
        "Nj",
        "latitudeOfFirstGridPointInDegrees",
        "longitudeOfFirstGridPointInDegrees",
        "latitudeOfLastGridPointInDegrees",
        "longitudeOfLastGridPointInDegrees",
        "latitudeOfSouthernPoleInDegrees",
        "longitudeOfSouthernPoleInDegrees",
    ]

    @classmethod
    def compute_coords(cls, **kwargs):
        Ni = kwargs["Ni"]
        Nj = kwargs["Nj"]
        latFirst = kwargs["latitudeOfFirstGridPointInDegrees"]
        latLast = kwargs["latitudeOfLastGridPointInDegrees"]
        lonFirst = kwargs["longitudeOfFirstGridPointInDegrees"]
        lonLast = kwargs["longitudeOfLastGridPointInDegrees"]
        latPole = kwargs["latitudeOfSouthernPoleInDegrees"]
        lonPole = kwargs["longitudeOfSouthernPoleInDegrees"]

        lons, lats = np.meshgrid(
            np.linspace(lonFirst, lonLast, Ni), np.linspace(latFirst, latLast, Nj)
        )

        lons, lats = rot_to_reg(lonPole, latPole, lons, lats)

        x = np.linspace(0, 1, Ni)
        y = np.linspace(0, 1, Nj)

        return {"lon": lons, "lat": lats, "x": x, "y": y}


grids = {g.gridType: g for g in GribGrid._subclasses}


def params_for_gridType(gridType):
    if gridType in grids:
        return grids[gridType].params
    else:
        return []


def varinfo2coords(varinfo):
    grid = grids[varinfo["attrs"]["gridType"]]
    return grid.compute_coords(**{k: varinfo["extra"][k] for k in grid.params})
