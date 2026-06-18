from decimal import Decimal

from app.schemas.lead_scoring import LeadScoringInput
from app.services.lead_scoring_service import LeadScoringService


def test_high_value_solar_quote_lead_is_hot():
    service = LeadScoringService()

    result = service.score(
        LeadScoringInput(
            name="Maria",
            city="Mossoró",
            average_energy_bill=Decimal("1200"),
            property_type="commercial",
            intent="solar_quote",
            has_solar_interest=True,
        )
    )

    # 20 (interest) + 25 (quote) + 35 (>=1000) + 15 (commercial) + 10 (city) + 5 (name)
    # = 110 raw, clamped to 100 by min(100, score)
    assert result.lead_score == 100
    assert result.lead_temperature == "hot"
    assert result.score_reasons


def test_empty_input_is_cold_with_zero_score():
    service = LeadScoringService()

    result = service.score(
        LeadScoringInput(
            name=None,
            city=None,
            average_energy_bill=None,
            property_type=None,
            intent=None,
            has_solar_interest=False,
        )
    )

    assert result.lead_score == 0
    assert result.lead_temperature == "cold"


def test_mid_value_residential_interest_is_hot():
    service = LeadScoringService()

    result = service.score(
        LeadScoringInput(
            name=None,
            city="Natal",
            average_energy_bill=Decimal("400"),
            property_type="residential",
            intent="solar_interest",
            has_solar_interest=True,
        )
    )

    # 20 (interest) + 15 (solar_interest) + 15 (300-499) + 10 (residential) + 10 (city) = 70
    assert result.lead_score == 70
    assert result.lead_temperature == "hot"
