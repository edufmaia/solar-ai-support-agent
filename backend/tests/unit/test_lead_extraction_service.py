from decimal import Decimal

from app.services.lead_extraction_service import LeadExtractionService


def test_extracts_city_bill_and_solar_interest_from_full_message():
    service = LeadExtractionService()

    result = service.extract(
        "Olá, moro em Mossoró, minha conta vem R$ 650 e tenho interesse em energia solar para minha casa"
    )

    assert result.city == "Mossoró"
    assert result.average_energy_bill == Decimal("650")
    assert result.property_type == "residential"
    assert result.intent == "solar_interest"
    assert result.has_solar_interest is True


def test_quote_keyword_sets_solar_quote_intent():
    service = LeadExtractionService()

    result = service.extract("Quero um orçamento de energia solar")

    assert result.intent == "solar_quote"
    assert result.has_solar_interest is True


def test_commercial_keyword_sets_commercial_property_type():
    service = LeadExtractionService()

    result = service.extract("Tenho uma loja e quero saber sobre energia solar")

    assert result.property_type == "commercial"


def test_message_without_relevant_data_returns_general_question():
    service = LeadExtractionService()

    result = service.extract("Bom dia, tudo bem?")

    assert result.intent == "general_question"
    assert result.has_solar_interest is False
    assert result.city is None
    assert result.average_energy_bill is None


def test_explicit_request_for_human_sets_wants_human():
    service = LeadExtractionService()

    assert service.extract("Quero falar com um atendente").wants_human is True
    assert service.extract("Prefiro falar com uma pessoa, não com robô").wants_human is True
    assert service.extract("Pode me transferir para um humano?").wants_human is True


def test_neutral_message_does_not_set_wants_human():
    service = LeadExtractionService()

    result = service.extract("Olá, tenho interesse em energia solar para minha casa")

    assert result.wants_human is False
