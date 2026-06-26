from decimal import ROUND_HALF_UP, Decimal

from ..schemas.solar import SolarPotentialResult
from .base import BaseSolarProvider
from .consumption import (
    PANEL_WATTS,
    TECH_REVIEW_KWP_THRESHOLD,
    panels_from_bill,
    seed_panels,
)


class MockSolarProvider(BaseSolarProvider):
    provider_name = "mock"

    def estimate(self, latitude, longitude, average_energy_bill) -> SolarPotentialResult:
        if latitude is None or longitude is None:
            return SolarPotentialResult(
                solar_data_available=False,
                confidence_level="unknown",
                requires_technical_review=False,
                raw_response={"provider": "mock", "reason": "missing_coordinates"},
            )

        estimate = panels_from_bill(average_energy_bill)
        if estimate is not None:
            panels = estimate.panels
            kwp = estimate.kwp
            confidence = "medium"
            raw = {
                "provider": "mock",
                "average_energy_bill": str(average_energy_bill),
                "monthly_kwh": str(estimate.monthly_kwh),
                "kwp": str(kwp),
            }
        else:
            panels = seed_panels(latitude, longitude)
            kwp = Decimal(panels) * Decimal(PANEL_WATTS) / Decimal(1000)
            confidence = "low"
            raw = {"provider": "mock", "reason": "no_bill_deterministic_seed"}

        estimated_kwp = kwp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        requires_review = estimated_kwp >= TECH_REVIEW_KWP_THRESHOLD or confidence == "low"

        return SolarPotentialResult(
            solar_data_available=True,
            estimated_panel_min=max(1, panels - 1),
            estimated_panel_max=panels + 1,
            estimated_system_kwp=estimated_kwp,
            confidence_level=confidence,
            requires_technical_review=requires_review,
            raw_response=raw,
        )
