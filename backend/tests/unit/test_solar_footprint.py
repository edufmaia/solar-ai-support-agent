import math
from decimal import Decimal

from app.config.settings import Settings
from app.solar.footprint_provider import FootprintSolarProvider
from app.solar.overpass_client import OverpassError

LAT0 = -5.79
LON0 = -35.21
M_PER_DEG_LAT = 111_320.0


def _square(side_m, center_lat=LAT0, center_lon=LON0):
    half_lat = (side_m / 2) / M_PER_DEG_LAT
    half_lon = (side_m / 2) / (M_PER_DEG_LAT * math.cos(math.radians(center_lat)))
    return [
        (center_lat - half_lat, center_lon - half_lon),
        (center_lat + half_lat, center_lon - half_lon),
        (center_lat + half_lat, center_lon + half_lon),
        (center_lat - half_lat, center_lon + half_lon),
    ]


class _FakeOverpass:
    def __init__(self, polygons=None, error=None):
        self._polygons = polygons or []
        self._error = error

    def buildings_around(self, latitude, longitude):
        if self._error is not None:
            raise self._error
        return self._polygons


def _provider(polygons=None, error=None):
    return FootprintSolarProvider(
        settings=Settings(),
        overpass_client=_FakeOverpass(polygons=polygons, error=error),
    )


def test_big_roof_small_bill_capped_by_consumption():
    # 20m square ~ 400 m2 -> usable 200 -> /2.6 ~ 76 panels; bill 350 -> 7 panels
    provider = _provider(polygons=[_square(20.0)])
    result = provider.estimate(Decimal(str(LAT0)), Decimal(str(LON0)), Decimal("350"))
    assert result.solar_data_available is True
    assert result.raw_response["source"] == "overpass"
    assert result.raw_response["panels_por_consumo"] == 7
    assert result.raw_response["panels_por_telhado"] > 7
    assert result.estimated_panel_min == 6 and result.estimated_panel_max == 8  # min == 7


def test_small_roof_big_bill_capped_by_roof():
    # 8m square ~ 64 m2 -> usable 32 -> /2.6 ~ 12 panels; bill 1200 -> 23 panels
    provider = _provider(polygons=[_square(8.0)])
    result = provider.estimate(Decimal(str(LAT0)), Decimal(str(LON0)), Decimal("1200"))
    assert result.raw_response["source"] == "overpass"
    roof = result.raw_response["panels_por_telhado"]
    assert result.estimated_panel_max == roof + 1
    assert roof < result.raw_response["panels_por_consumo"]


def test_no_building_falls_back_to_consumption():
    result = _provider(polygons=[]).estimate(Decimal(str(LAT0)), Decimal(str(LON0)), Decimal("350"))
    assert result.solar_data_available is True
    assert result.raw_response["source"] == "consumption_fallback"
    assert result.estimated_panel_min == 6 and result.estimated_panel_max == 8


def test_overpass_error_falls_back_to_consumption():
    result = _provider(error=OverpassError("down")).estimate(
        Decimal(str(LAT0)), Decimal(str(LON0)), Decimal("350")
    )
    assert result.raw_response["source"] == "consumption_fallback"
    assert result.estimated_panel_max == 8


def test_missing_coordinates_returns_no_data():
    result = _provider(polygons=[_square(20.0)]).estimate(None, None, Decimal("350"))
    assert result.solar_data_available is False
    assert result.confidence_level == "unknown"


def test_raw_response_includes_chosen_roof_polygon():
    square = _square(20.0)
    result = _provider(polygons=[square]).estimate(
        Decimal(str(LAT0)), Decimal(str(LON0)), Decimal("350")
    )
    expected = [[round(la, 6), round(lo, 6)] for la, lo in square]
    assert result.raw_response["roof_polygon"] == expected


def test_no_roof_polygon_when_no_building():
    result = _provider(polygons=[]).estimate(Decimal(str(LAT0)), Decimal(str(LON0)), Decimal("350"))
    assert result.raw_response.get("roof_polygon") is None
