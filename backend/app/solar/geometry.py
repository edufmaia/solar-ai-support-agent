import math

EARTH_RADIUS_M = 6_378_137.0


def _project(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Equirectangular projection to local meters around the polygon centroid."""
    lat0 = sum(p[0] for p in points) / len(points)
    cos_lat0 = math.cos(math.radians(lat0))
    lon0 = points[0][1]
    xy = []
    for lat, lon in points:
        x = math.radians(lon - lon0) * cos_lat0 * EARTH_RADIUS_M
        y = math.radians(lat - lat0) * EARTH_RADIUS_M
        xy.append((x, y))
    return xy


def polygon_area_m2(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    xy = _project(points)
    area2 = 0.0
    n = len(xy)
    for i in range(n):
        x1, y1 = xy[i]
        x2, y2 = xy[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
    return abs(area2) / 2.0


def polygon_centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Average of the ring's vertices, as (lat, lon)."""
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    """Ray casting in (lat, lon) degree space (lon = x, lat = y)."""
    if len(polygon) < 3:
        return False
    py, px = point  # lat, lon
    inside = False
    n = len(polygon)
    for i in range(n):
        ay, ax = polygon[i]
        by, bx = polygon[(i + 1) % n]
        if (ay > py) != (by > py):
            x_cross = (bx - ax) * (py - ay) / (by - ay) + ax
            if px < x_cross:
                inside = not inside
    return inside
