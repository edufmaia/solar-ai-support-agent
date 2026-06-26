from uuid import uuid4

from app.llm.mock_provider import MockLLMProvider
from app.schemas.llm import LLMRequest

PHONE = "84999990000"


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


def test_geospatial_with_contact_reports_panels_and_hands_off():
    response = MockLLMProvider().generate_response(
        _request(
            lead_data={"address": "Rua das Flores, 123", "phone": PHONE},
            geospatial=_geospatial_with_solar(),
        )
    )
    assert response.next_state == "handed_off_to_specialist"
    assert "especialista" in response.content.lower()
    # the agent verbalizes the estimated panel quantity for the consumption
    assert "12" in response.content and "14" in response.content
    assert "placa" in response.content.lower()
    # the handoff message references the real contact it will use
    assert PHONE in response.content


def test_geospatial_without_contact_reports_panels_and_collects_contact():
    response = MockLLMProvider().generate_response(
        _request(
            lead_data={"address": "Rua das Flores, 123"},  # no phone
            geospatial=_geospatial_with_solar(),
        )
    )
    # still reports the estimate (no more ignoring a completed analysis)
    assert "12" in response.content and "14" in response.content
    assert "placa" in response.content.lower()
    # but collects contact instead of falsely claiming a handoff
    assert response.next_state == "awaiting_contact"
    assert "telefone" in response.content.lower() or "whatsapp" in response.content.lower()
    assert "encaminhei" not in response.content.lower()


def test_post_analysis_with_known_name_asks_only_for_phone():
    # don't re-ask a name we already have; request only the missing phone.
    response = MockLLMProvider().generate_response(
        _request(
            lead_data={"address": "Rua das Flores, 123", "name": "Eduardo Freire Maia"},
            geospatial=_geospatial_with_solar(),
        )
    )
    assert response.next_state == "awaiting_contact"
    assert "telefone" in response.content.lower() or "whatsapp" in response.content.lower()
    assert "nome e telefone" not in response.content.lower()


def test_warm_lead_with_geospatial_reports_analysis_instead_of_looping():
    # regression for the reported bug: a warm lead that already ran the analysis
    # must report it, not keep asking for data.
    response = MockLLMProvider().generate_response(
        _request(
            lead_temperature="warm",
            lead_data={"address": "Rua X, 1"},  # no phone
            geospatial=_geospatial_with_solar(),
        )
    )
    assert "placa" in response.content.lower()
    assert response.next_state == "awaiting_contact"


def test_warm_lead_with_geospatial_and_contact_hands_off():
    response = MockLLMProvider().generate_response(
        _request(
            lead_temperature="warm",
            lead_data={"address": "Rua X, 1", "phone": PHONE},
            geospatial=_geospatial_with_solar(),
        )
    )
    assert response.next_state == "handed_off_to_specialist"
    assert "especialista" in response.content.lower()


def test_geospatial_without_solar_with_contact_hands_off():
    response = MockLLMProvider().generate_response(
        _request(lead_data={"address": "Rua X", "phone": PHONE}, geospatial={"found": True})
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
