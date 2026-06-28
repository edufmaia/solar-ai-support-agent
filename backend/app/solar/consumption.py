import hashlib
from dataclasses import dataclass
from decimal import Decimal
from math import ceil

TARIFF_BRL_PER_KWH = Decimal("0.95")  # tarifa media residencial BR
PEAK_SUN_HOURS = Decimal("4.5")  # horas de sol pico medias BR
PERFORMANCE_RATIO = Decimal("0.75")  # perdas do sistema
PANEL_WATTS = 550  # modulo de referencia
TECH_REVIEW_KWP_THRESHOLD = Decimal("10")  # acima disso, exige revisao tecnica


@dataclass(frozen=True)
class ConsumptionEstimate:
    panels: int
    kwp: Decimal  # unquantized
    monthly_kwh: Decimal


def panels_from_bill(average_energy_bill: Decimal | None) -> ConsumptionEstimate | None:
    if average_energy_bill is None or average_energy_bill <= 0:
        return None
    monthly_kwh = average_energy_bill / TARIFF_BRL_PER_KWH
    daily_kwh = monthly_kwh / Decimal(30)
    kwp = daily_kwh / (PEAK_SUN_HOURS * PERFORMANCE_RATIO)
    panels = ceil(kwp * Decimal(1000) / Decimal(PANEL_WATTS))
    return ConsumptionEstimate(panels=panels, kwp=kwp, monthly_kwh=monthly_kwh)


def seed_panels(latitude, longitude) -> int:
    """Deterministic 6..12 panels from coordinates, for the no-bill fallback."""
    seed = int(hashlib.sha256(f"{latitude},{longitude}".encode()).hexdigest(), 16)
    return 6 + (seed % 7)
