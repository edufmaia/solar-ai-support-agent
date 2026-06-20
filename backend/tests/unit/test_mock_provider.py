from uuid import uuid4

from app.llm.mock_provider import MockLLMProvider
from app.schemas.llm import LLMRequest


def _request(**overrides) -> LLMRequest:
    base = dict(conversation_id=uuid4(), user_message="oi", lead_temperature="hot")
    base.update(overrides)
    return LLMRequest(**base)


def test_hot_without_address_asks_for_address():
    response = MockLLMProvider().generate_response(_request(lead_data={}))
    assert response.next_state == "ready_for_geospatial_pre_analysis"
    assert "endereço" in response.content.lower()


def test_hot_with_address_asks_for_consent():
    response = MockLLMProvider().generate_response(
        _request(lead_data={"address": "Rua das Flores, 123"})
    )
    assert response.next_state == "awaiting_geospatial_consent"


def _geospatial_with_solar():
    return {
        "found": True,
        "solar": {
            "solar_data_available": True,
            "estimated_panel_min": 12,
            "estimated_panel_max": 14,
            "estimated_system_kwp": 6.4,
            "confidence_level": "medium",
            "requires_technical_review": False,
        },
    }


def test_hot_after_geospatial_reports_panels_and_hands_off():
    response = MockLLMProvider().generate_response(
        _request(lead_data={"address": "Rua das Flores, 123"}, geospatial=_geospatial_with_solar())
    )
    assert response.next_state == "handed_off_to_specialist"
    assert "especialista" in response.content.lower()
    # the agent verbalizes the estimated panel quantity for the consumption
    assert "12" in response.content and "14" in response.content
    assert "placa" in response.content.lower()


def test_hot_after_geospatial_without_solar_still_hands_off():
    response = MockLLMProvider().generate_response(
        _request(lead_data={"address": "Rua X"}, geospatial={"found": True})
    )
    assert response.next_state == "handed_off_to_specialist"
    assert "especialista" in response.content.lower()


def test_hot_progression_varies_response_text():
    provider = MockLLMProvider()
    no_address = provider.generate_response(_request(lead_data={})).content
    with_address = provider.generate_response(
        _request(lead_data={"address": "Rua X, 1"})
    ).content
    after_geo = provider.generate_response(
        _request(lead_data={"address": "Rua X, 1"}, geospatial=_geospatial_with_solar())
    ).content
    # three distinct messages instead of one repeated line
    assert len({no_address, with_address, after_geo}) == 3
