import math

def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    R = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = math.sin(dlat/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_within_campus(campus, lat: float, lng: float) -> bool:
    d = _haversine_m(
        float(campus.center_lat),
        float(campus.center_lng),
        lat,
        lng,
    )
    return d <= float(campus.radius_m)
