import hashlib
from decimal import ROUND_HALF_UP, Decimal
from math import ceil

from ..schemas.solar import SolarPotentialResult
from .base import BaseSolarProvider

TARIFF_BRL_PER_KWH = Decimal("0.95")       # tarifa media residencial BR
PEAK_SUN_HOURS = Decimal("4.5")            # horas de sol pico medias BR
PERFORMANCE_RATIO = Decimal("0.75")        # perdas do sistema
PANEL_WATTS = 550                          # modulo de referencia
TECH_REVIEW_KWP_THRESHOLD = Decimal("10")  # acima disso, exige revisao tecnica


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

        if average_energy_bill is not None and average_energy_bill > 0:
            monthly_kwh = average_energy_bill / TARIFF_BRL_PER_KWH
            daily_kwh = monthly_kwh / Decimal(30)
            kwp = daily_kwh / (PEAK_SUN_HOURS * PERFORMANCE_RATIO)
            panels = ceil(kwp * Decimal(1000) / Decimal(PANEL_WATTS))
            confidence = "medium"
            raw = {
                "provider": "mock",
                "average_energy_bill": str(average_energy_bill),
                "monthly_kwh": str(monthly_kwh),
                "kwp": str(kwp),
            }
        else:
            seed = int(hashlib.sha256(f"{latitude},{longitude}".encode()).hexdigest(), 16)
            panels = 6 + (seed % 7)  # 6..12 paineis demonstrativos, deterministico
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
