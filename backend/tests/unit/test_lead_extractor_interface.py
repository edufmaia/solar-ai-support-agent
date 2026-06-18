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
