import math


EARTH_RADIUS_M = 6371000.0


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two geographic points using the Haversine formula.

    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees)
        lat2, lon2: Latitude and longitude of point 2 (in degrees)

    Returns:
        Distance in meters
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return EARTH_RADIUS_M * c


def destination_point(lat, lon, bearing_deg, distance_m):
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing = math.radians(bearing_deg)

    dr = distance_m / EARTH_RADIUS_M

    dest_lat = math.asin(
        math.sin(lat_rad) * math.cos(dr)
        + math.cos(lat_rad) * math.sin(dr) * math.cos(bearing)
    )
    dest_lon = lon_rad + math.atan2(
        math.sin(bearing) * math.sin(dr) * math.cos(lat_rad),
        math.cos(dr) - math.sin(lat_rad) * math.sin(dest_lat),
    )

    return math.degrees(dest_lat), math.degrees(dest_lon)


def generate_petal(lat, lon, azimuth, beamwidth, radius_m, points=24):
    half = beamwidth / 2.0
    start = azimuth - half
    end = azimuth + half
    step = max(1, int(beamwidth / max(1, points)))

    coords = [(lon, lat)]
    angle = start
    while angle <= end:
        dlat, dlon = destination_point(lat, lon, angle, radius_m)
        coords.append((dlon, dlat))
        angle += step
    dlat, dlon = destination_point(lat, lon, end, radius_m)
    coords.append((dlon, dlat))
    coords.append((lon, lat))
    return coords
