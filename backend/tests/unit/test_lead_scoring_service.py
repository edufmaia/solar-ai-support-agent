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


from app.schemas.lead_scoring import LeadScoringResult


def _base(score=50):
    return LeadScoringResult(lead_score=score, lead_temperature="warm", score_reasons=["base"])


def _geo(solar_available=True, kwp=12.0, confidence="high", tech_review=False):
    return {
        "found": True,
        "solar": {
            "solar_data_available": solar_available,
            "estimated_system_kwp": kwp,
            "confidence_level": confidence,
            "requires_technical_review": tech_review,
        },
    }


def test_apply_geospatial_none_returns_base_unchanged():
    base = _base()
    result = LeadScoringService().apply_geospatial(base, None)
    assert result.lead_score == 50
    assert result.score_reasons == ["base"]


def test_apply_geospatial_without_solar_data_unchanged():
    result = LeadScoringService().apply_geospatial(_base(), _geo(solar_available=False))
    assert result.lead_score == 50
    assert result.score_reasons == ["base"]


def test_apply_geospatial_high_potential_adds_delta_and_recomputes_temperature():
    result = LeadScoringService().apply_geospatial(_base(50), _geo(kwp=12.0, confidence="high"))
    assert result.lead_score == 80  # 50 + 10 + 15 + 5
    assert result.lead_temperature == "hot"
    assert "Potencial solar alto (>= 10 kWp)" in result.score_reasons
    assert result.score_reasons[0] == "base"


def test_apply_geospatial_medium_tier():
    result = LeadScoringService().apply_geospatial(_base(50), _geo(kwp=6.0, confidence="medium"))
    assert result.lead_score == 73  # 50 + 10 + 10 + 3


def test_apply_geospatial_low_potential_low_confidence():
    result = LeadScoringService().apply_geospatial(_base(50), _geo(kwp=2.0, confidence="low"))
    assert result.lead_score == 65  # 50 + 10 + 5 + 0


def test_apply_geospatial_requires_technical_review_adds_reason_only():
    without = LeadScoringService().apply_geospatial(_base(50), _geo(kwp=12.0, confidence="high", tech_review=False))
    with_review = LeadScoringService().apply_geospatial(_base(50), _geo(kwp=12.0, confidence="high", tech_review=True))
    assert with_review.lead_score == without.lead_score  # flag adds no numeric weight
    assert "Requer revisão técnica (consultor humano)" in with_review.score_reasons
    assert "Requer revisão técnica (consultor humano)" not in without.score_reasons


def test_apply_geospatial_clamps_at_100():
    result = LeadScoringService().apply_geospatial(_base(90), _geo(kwp=12.0, confidence="high"))
    assert result.lead_score == 100


def test_temperature_for_thresholds():
    service = LeadScoringService()
    assert service._temperature_for(70) == "hot"
    assert service._temperature_for(69) == "warm"
    assert service._temperature_for(40) == "warm"
    assert service._temperature_for(39) == "cold"
