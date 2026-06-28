import pytest
from app.schemas.lead_extraction import LeadExtractionResult
from app.services.lead_extraction_service import LeadExtractionService
from app.services.lead_extractor import LeadExtractor


def test_lead_extraction_service_implements_interface():
    assert isinstance(LeadExtractionService(), LeadExtractor)


def test_lead_extractor_is_abstract():
    with pytest.raises(TypeError):
        LeadExtractor()


def test_has_relevant_data_true_when_only_phone_present():
    result = LeadExtractionResult(phone="84999998888")

    assert result.has_relevant_data() is True


def test_has_relevant_data_true_when_only_address_present():
    result = LeadExtractionResult(address="Rua das Flores, 123")

    assert result.has_relevant_data() is True


def test_event_payload_includes_phone_and_address_when_present():
    result = LeadExtractionResult(phone="84999998888", address="Rua das Flores, 123")

    payload = result.to_event_payload()

    assert payload["phone"] == "84999998888"
    assert payload["address"] == "Rua das Flores, 123"


def test_event_payload_omits_phone_and_address_when_absent():
    payload = LeadExtractionResult().to_event_payload()

    assert "phone" not in payload
    assert "address" not in payload


def test_regex_extractor_accepts_and_ignores_context_kwargs():
    service = LeadExtractionService()
    result = service.extract(
        "me chamo Ana",
        history=[{"role": "assistant", "content": "Qual seu nome?"}],
        known_lead={"city": "Natal"},
    )
    assert result.name == "Ana"


def test_has_relevant_data_true_when_only_email_present():
    result = LeadExtractionResult(email="contato.eduardofmaia@gmail.com")
    assert result.has_relevant_data() is True


def test_event_payload_includes_email_when_present():
    payload = LeadExtractionResult(email="contato.eduardofmaia@gmail.com").to_event_payload()
    assert payload["email"] == "contato.eduardofmaia@gmail.com"


def test_event_payload_omits_email_when_absent():
    assert "email" not in LeadExtractionResult().to_event_payload()
