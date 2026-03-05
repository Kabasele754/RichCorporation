from math import radians, sin, cos, sqrt, atan2

# =========================================================
# Distance (Haversine) en mètres
# =========================================================
def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


# =========================================================
# GEO: Room tag
# =========================================================
def is_within_room_tag(tag, lat: float, lng: float, extra_m: float = 0.0):
    """
    Retourne (ok, distance_m, allowed_m).
    Si tag n'a pas de lat/lng -> on ne bloque pas.
    """
    if not tag or tag.latitude is None or tag.longitude is None:
        return True, None, None

    dist = haversine_m(lat, lng, float(tag.latitude), float(tag.longitude))
    base = float(tag.radius_m or 0.0)
    allowed = base + float(extra_m or 0.0)

    return dist <= allowed, dist, allowed


# =========================================================
# GEO: Campus (avec tolérance)
# =========================================================
def is_within_campus(campus, lat: float, lng: float, extra_m: float = 0.0):
    """
    Retourne (ok, distance_m, allowed_m)

    - Si campus n'a pas center_lat/center_lng -> on ne bloque pas (setup friendly)
    - extra_m permet la tolérance GPS (accuracy indoor)
    """
    if not campus:
        return True, None, None

    if campus.center_lat is None or campus.center_lng is None:
        # campus pas configuré => ne bloque pas la configuration des rooms
        return True, None, None

    try:
        c_lat = float(campus.center_lat)
        c_lng = float(campus.center_lng)
    except Exception:
        return True, None, None

    dist = haversine_m(c_lat, c_lng, float(lat), float(lng))
    base = float(campus.radius_m or 0.0)
    allowed = base + float(extra_m or 0.0)

    return dist <= allowed, dist, allowed