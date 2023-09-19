
import numpy as np
import eccodes as ec

pi = np.pi
rad = pi / 180.0
radinv = 1.0 / rad


def rot_to_reg(pole_lon, pole_lat, lon, lat):
    """Rotates from rotated grid to regular grid

    Parameters
    ----------
    pole_lon : float
        Longitude of pole in degrees
    pole_lat : float
        Latitude of pole in degrees
    lon : float, list
        Longitudes of points in grid. Can also be a single point.
    lat : float, list
        Latitudes of points in grid. Can also be a single point.

    Returns
    -------
    lon1 : float, list
        Longitudes of regular grid. Same shape as input.
    lat1 : float, list
        Latitudes  of regular grid. Same shape as input.
    """
    sin_pole = np.sin(np.deg2rad(pole_lat + 90.0))
    cos_pole = np.cos(np.deg2rad(pole_lat + 90.0))

    sin_lon = np.sin(np.deg2rad(lon))
    cos_lon = np.cos(np.deg2rad(lon))
    sin_lat = np.sin(np.deg2rad(lat))
    cos_lat = np.cos(np.deg2rad(lat))

    lat_tmp = cos_pole * sin_lat + sin_pole * cos_lat * cos_lon

    lat_tmp = np.clip(lat_tmp, -1.0, 1.0)

    lat2 = np.rad2deg(np.arcsin(lat_tmp))

    cos_lat2 = np.cos(lat2 * rad)

    cos_tmp = (cos_pole * cos_lat * cos_lon - sin_pole * sin_lat) / cos_lat2

        cos_tmp = np.clip(cos_tmp, -1.0, 1.0)

    tmp_sin_lon = cos_lat * sin_lon / cos_lat2
    tmp_cos_lon = np.rad2deg(np.arccos(cos_tmp))

    tmp_cos_lon = np.where(tmp_sin_lon < 0.0, -tmp_cos_lon, tmp_cos_lon)

    lon2 = tmp_cos_lon + pole_lon

    return lon2, lat2


def get_gids(gribfile: str, TextIOWrapper: bool = False) -> list:
    """Get GribIDs (gid) for all the messages in one gribfile

    Parameters
    ----------
    gribfile : str
        path to gribfile
    TextIOWrapper : bool
        if file is open send the object instead and set TextIOWrapper to True

    Returns
    -------
    list
        list of grib-ids
    """

    if not TextIOWrapper:
        f = open(gribfile, "rb")
        msg_count = ec.codes_count_in_file(f)
        gids = [ec.codes_grib_new_from_file(f) for i in range(msg_count)]
        f.close()
    else:
        # gribfile has already been opened into a TextIOWrapper in this case
        msg_count = ec.codes_count_in_file(gribfile)
        gids = np.zeros(msg_count, dtype=int)
        for i in range(msg_count):
            gids[i] = ec.codes_grib_new_from_file(gribfile)

    return gids


def get_latlons(gribfile: str) -> tuple:
    """Get latitudes and longitudes from file. Uses pygrib as
    eccodes have no easy interface for that.

    Parameters
    ----------
    gribfile : str
        Path to gribfile

    Returns
    -------
    tuple
        tuple of latitudes, longitudes
    """

    gids = get_gids(gribfile)
    gid = gids[0]
    Ni = ec.codes_get(gid, "Ni")
    Nj = ec.codes_get(gid, "Nj")

    latFirst = ec.codes_get(gid, "latitudeOfFirstGridPointInDegrees")
    latLast = ec.codes_get(gid, "latitudeOfLastGridPointInDegrees")
    lonFirst = ec.codes_get(gid, "longitudeOfFirstGridPointInDegrees")
    lonLast = ec.codes_get(gid, "longitudeOfLastGridPointInDegrees")

    latPole = ec.codes_get(gid, "latitudeOfSouthernPoleInDegrees")
    lonPole = ec.codes_get(gid, "longitudeOfSouthernPoleInDegrees")

    gridType = ec.codes_get(gid, "gridType")

    lons, lats = np.meshgrid(
        np.linspace(lonFirst, lonLast, Ni), np.linspace(latFirst, latLast, Nj)
    )

    if gridType == "rotated_ll":
        lons, lats = rot_to_reg(lonPole, latPole, lons, lats)
    else:
        raise NotImplementedError(gridType)

    return lats, lons
