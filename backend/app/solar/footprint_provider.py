from decimal import ROUND_HALF_UP, Decimal
from math import cos, floor, radians
from typing import Any

from ..config.settings import Settings, get_settings
from ..schemas.solar import SolarConfidence, SolarPotentialResult
from .base import BaseSolarProvider
from .consumption import (
    PANEL_WATTS,
    TECH_REVIEW_KWP_THRESHOLD,
    panels_from_bill,
    seed_panels,
)
from .geometry import point_in_polygon, polygon_area_m2, polygon_centroid
from .overpass_client import OverpassClient, OverpassError


class FootprintSolarProvider(BaseSolarProvider):
    provider_name = "footprint"

    def __init__(self, settings: Settings | None = None, overpass_client=None) -> None:
        self.settings = settings or get_settings()
        self.overpass_client = overpass_client or OverpassClient(self.settings)

    @staticmethod
    def _distance_m2(point: tuple[float, float], polygon: list) -> float:
        """Squared distance (in meters²) from a (lat, lon) point to a polygon's
        centroid, used to rank candidate buildings by proximity."""
        plat, plon = point
        clat, clon = polygon_centroid(polygon)
        dy = (clat - plat) * 111_320.0
        dx = (clon - plon) * 111_320.0 * cos(radians(plat))
        return dy * dy + dx * dx

    def _roof_panels(
        self, latitude, longitude
    ) -> tuple[int | None, float | None, float | None, list | None]:
        """Returns (panels, footprint_area_m2, usable_area_m2, chosen_polygon).

        ``chosen_polygon`` is the building ring used for the estimate (a list of
        ``(lat, lon)`` points), or ``None`` when no building was found.
        """
        try:
            polygons = self.overpass_client.buildings_around(latitude, longitude)
        except OverpassError:
            return None, None, None, None
        if not polygons:
            return None, None, None, None

        point = (float(latitude), float(longitude))
        chosen = next((p for p in polygons if point_in_polygon(point, p)), None)
        if chosen is None:
            # No building contains the geocoded point (e.g. it resolved to the
            # street). Pick the NEAREST building — more likely the actual address
            # than the largest one nearby.
            chosen = min(polygons, key=lambda p: self._distance_m2(point, p))

        area = polygon_area_m2(chosen)
        usable = area * self.settings.roof_usable_factor
        panels = floor(usable / self.settings.panel_area_m2)
        if panels < 1:
            return None, area, usable, chosen
        return panels, area, usable, chosen

    def estimate(self, latitude, longitude, average_energy_bill) -> SolarPotentialResult:
        if latitude is None or longitude is None:
            return SolarPotentialResult(
                solar_data_available=False,
                confidence_level="unknown",
                requires_technical_review=False,
                raw_response={"provider": "footprint", "reason": "missing_coordinates"},
            )

        consumption = panels_from_bill(average_energy_bill)
        roof_panels, area_m2, usable_m2, roof_polygon = self._roof_panels(latitude, longitude)

        consumo_panels = consumption.panels if consumption is not None else None

        if consumption is not None and roof_panels is not None:
            panels = min(consumption.panels, roof_panels)
            confidence: SolarConfidence = "medium"
            source = "overpass"
        elif consumption is not None:
            panels = consumption.panels
            confidence = "medium"
            source = "consumption_fallback"
        elif roof_panels is not None:
            panels = roof_panels
            confidence = "low"
            source = "overpass_no_bill"
        else:
            panels = seed_panels(latitude, longitude)
            confidence = "low"
            source = "seed_fallback"

        kwp = Decimal(panels) * Decimal(PANEL_WATTS) / Decimal(1000)
        estimated_kwp = kwp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        requires_review = estimated_kwp >= TECH_REVIEW_KWP_THRESHOLD or confidence == "low"

        raw: dict[str, Any] = {
            "provider": "footprint",
            "source": source,
            "panels_por_consumo": consumo_panels,
            "panels_por_telhado": roof_panels,
            "area_footprint_m2": round(area_m2, 1) if area_m2 is not None else None,
            "area_util_m2": round(usable_m2, 1) if usable_m2 is not None else None,
        }
        if roof_polygon is not None:
            raw["roof_polygon"] = [[round(lat, 6), round(lon, 6)] for lat, lon in roof_polygon]

        return SolarPotentialResult(
            solar_data_available=True,
            estimated_panel_min=max(1, panels - 1),
            estimated_panel_max=panels + 1,
            estimated_system_kwp=estimated_kwp,
            confidence_level=confidence,
            requires_technical_review=requires_review,
            raw_response=raw,
        )
