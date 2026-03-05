import math

from math import radians, sin, cos, sqrt, atan2

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(p1)*cos(p2)*sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def is_within_room_tag(tag, lat: float, lng: float):
    """
    Retourne (ok, distance_m).
    Si tag n'a pas de lat/lng -> on ne bloque pas.
    """
    if not tag or tag.latitude is None or tag.longitude is None:
        return True, None
    dist = haversine_m(lat, lng, float(tag.latitude), float(tag.longitude))
    limit_m = float(tag.radius_m or 0)
    return dist <= limit_m, dist


def is_within_campus(campus, lat: float, lng: float) -> bool:
    d = haversine_m(
        float(campus.center_lat),
        float(campus.center_lng),
        lat,
        lng,
    )
    return d <= float(campus.radius_m)
