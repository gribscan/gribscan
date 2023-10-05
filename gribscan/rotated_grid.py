
import numpy as np

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

    cos_lat2 = np.cos(np.deg2rad(lat2))

    cos_tmp = (cos_pole * cos_lat * cos_lon - sin_pole * sin_lat) / cos_lat2
    cos_tmp = np.clip(cos_tmp, -1.0, 1.0)

    tmp_sin_lon = cos_lat * sin_lon / cos_lat2
    tmp_cos_lon = np.rad2deg(np.arccos(cos_tmp))

    tmp_cos_lon = np.where(tmp_sin_lon < 0.0, -tmp_cos_lon, tmp_cos_lon)

    lon2 = tmp_cos_lon + pole_lon

    return lon2, lat2
