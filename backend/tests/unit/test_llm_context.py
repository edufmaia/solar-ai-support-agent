from uuid import uuid4

from app.llm.context import (
    build_response_context_block,
    build_response_instructions,
    build_response_messages,
    geospatial_prompt_section,
)
from app.schemas.llm import LLMRequest


def _req(**kw):
    base = dict(conversation_id=uuid4(), user_message="oi")
    base.update(kw)
    return LLMRequest(**base)


def test_instructions_forbid_letter_placeholders():
    text = build_response_instructions()
    assert "[Seu Nome]" in text and "assinatura" in text.lower()
    assert "não" in text.lower()


def test_messages_map_history_roles():
    req = _req(history=[
        {"role": "assistant", "content": "Qual seu nome?"},
        {"role": "user", "content": "Eduardo Freire Maia"},
    ])
    msgs = build_response_messages(req)
    assert msgs == [
        {"role": "assistant", "content": "Qual seu nome?"},
        {"role": "user", "content": "Eduardo Freire Maia"},
    ]


def test_messages_fallback_to_current_message_when_no_history():
    msgs = build_response_messages(_req(user_message="olá"))
    assert msgs == [{"role": "user", "content": "olá"}]


def test_context_block_lists_known_lead_fields():
    block = build_response_context_block(_req(lead_data={"name": "Eduardo", "email": "a@b.com"}))
    assert "Eduardo" in block and "a@b.com" in block


def test_empty_when_no_geospatial():
    assert geospatial_prompt_section(None) == ""
    assert geospatial_prompt_section({}) == ""


def test_empty_when_no_solar_data():
    section = geospatial_prompt_section({"found": True, "solar": {"solar_data_available": False}})
    assert section == ""


def test_includes_panel_range_and_kwp():
    section = geospatial_prompt_section(
        {
            "formatted_address": "Rua das Flores, 123, Natal",
            "solar": {
                "solar_data_available": True,
                "estimated_panel_min": 12,
                "estimated_panel_max": 14,
                "estimated_system_kwp": 6.4,
                "confidence_level": "medium",
                "requires_technical_review": True,
            },
        }
    )
    assert "12" in section and "14" in section
    assert "6.4" in section
    assert "Rua das Flores" in section
    assert "revisão técnica" in section.lower()
