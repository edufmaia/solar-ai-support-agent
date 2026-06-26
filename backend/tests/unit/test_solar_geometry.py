import math

from app.solar.geometry import point_in_polygon, polygon_area_m2

LAT0 = -5.79
LON0 = -35.21
M_PER_DEG_LAT = 111_320.0


def _square(side_m):
    dlat = side_m / M_PER_DEG_LAT
    dlon = side_m / (M_PER_DEG_LAT * math.cos(math.radians(LAT0)))
    return [
        (LAT0, LON0),
        (LAT0 + dlat, LON0),
        (LAT0 + dlat, LON0 + dlon),
        (LAT0, LON0 + dlon),
    ]


def test_area_of_10m_square_is_about_100m2():
    area = polygon_area_m2(_square(10.0))
    assert abs(area - 100.0) < 3.0


def test_point_inside_and_outside():
    sq = _square(20.0)
    center = (LAT0 + 10.0 / M_PER_DEG_LAT, LON0 + 10.0 / (M_PER_DEG_LAT * math.cos(math.radians(LAT0))))
    assert point_in_polygon(center, sq) is True
    assert point_in_polygon((LAT0 + 1.0, LON0 + 1.0), sq) is False
