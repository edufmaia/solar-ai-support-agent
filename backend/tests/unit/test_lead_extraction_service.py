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


def test_event_payload_includes_wants_human():
    service = LeadExtractionService()

    payload = service.extract("Quero falar com um atendente").to_event_payload()

    assert payload["wants_human"] is True


def test_extracts_phone_in_various_formats_as_digits():
    service = LeadExtractionService()

    assert service.extract("Meu telefone é (84) 99999-8888").phone == "84999998888"
    assert service.extract("me liga no 84999998888").phone == "84999998888"
    assert service.extract("contato +55 84 99999-8888").phone == "5584999998888"


def test_does_not_capture_energy_bill_as_phone():
    service = LeadExtractionService()

    result = service.extract("minha conta vem R$ 650 e tenho interesse em energia solar")

    assert result.phone is None
    assert result.average_energy_bill is not None  # the bill is still extracted


def test_message_without_phone_returns_none():
    service = LeadExtractionService()

    assert service.extract("Olá, tenho interesse em energia solar").phone is None


def test_extracts_address_when_logradouro_present():
    service = LeadExtractionService()

    a1 = service.extract("Meu endereço é Rua das Flores, 123").address
    assert a1 is not None
    assert "Rua das Flores" in a1
    assert "123" in a1

    a2 = service.extract("Fica na Avenida Brasil, 4500, bairro Centro").address
    assert a2 is not None
    assert "Avenida Brasil" in a2
    assert "4500" in a2


def test_message_without_address_returns_none():
    service = LeadExtractionService()

    assert service.extract("Olá, tenho interesse em energia solar para minha casa").address is None
