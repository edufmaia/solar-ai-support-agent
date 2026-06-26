from decimal import ROUND_HALF_UP, Decimal
from math import floor

from ..config.settings import Settings, get_settings
from ..schemas.solar import SolarPotentialResult
from .base import BaseSolarProvider
from .consumption import (
    PANEL_WATTS,
    TECH_REVIEW_KWP_THRESHOLD,
    panels_from_bill,
    seed_panels,
)
from .geometry import point_in_polygon, polygon_area_m2
from .overpass_client import OverpassClient, OverpassError


class FootprintSolarProvider(BaseSolarProvider):
    provider_name = "footprint"

    def __init__(self, settings: Settings | None = None, overpass_client=None) -> None:
        self.settings = settings or get_settings()
        self.overpass_client = overpass_client or OverpassClient(self.settings)

    def _roof_panels(self, latitude, longitude) -> tuple[int | None, float | None, float | None]:
        """Returns (panels, footprint_area_m2, usable_area_m2) or (None, None, None)."""
        try:
            polygons = self.overpass_client.buildings_around(latitude, longitude)
        except OverpassError:
            return None, None, None
        if not polygons:
            return None, None, None

        point = (float(latitude), float(longitude))
        chosen = next((p for p in polygons if point_in_polygon(point, p)), None)
        if chosen is None:
            chosen = max(polygons, key=polygon_area_m2)

        area = polygon_area_m2(chosen)
        usable = area * self.settings.roof_usable_factor
        panels = floor(usable / self.settings.panel_area_m2)
        if panels < 1:
            return None, area, usable
        return panels, area, usable

    def estimate(self, latitude, longitude, average_energy_bill) -> SolarPotentialResult:
        if latitude is None or longitude is None:
            return SolarPotentialResult(
                solar_data_available=False,
                confidence_level="unknown",
                requires_technical_review=False,
                raw_response={"provider": "footprint", "reason": "missing_coordinates"},
            )

        consumption = panels_from_bill(average_energy_bill)
        roof_panels, area_m2, usable_m2 = self._roof_panels(latitude, longitude)

        consumo_panels = consumption.panels if consumption is not None else None

        if consumption is not None and roof_panels is not None:
            panels = min(consumption.panels, roof_panels)
            confidence = "medium"
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

        raw = {
            "provider": "footprint",
            "source": source,
            "panels_por_consumo": consumo_panels,
            "panels_por_telhado": roof_panels,
            "area_footprint_m2": round(area_m2, 1) if area_m2 is not None else None,
            "area_util_m2": round(usable_m2, 1) if usable_m2 is not None else None,
        }

        return SolarPotentialResult(
            solar_data_available=True,
            estimated_panel_min=max(1, panels - 1),
            estimated_panel_max=panels + 1,
            estimated_system_kwp=estimated_kwp,
            confidence_level=confidence,
            requires_technical_review=requires_review,
            raw_response=raw,
        )
