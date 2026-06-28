import pytest
from app.llm.extraction.prompt import (
    LEAD_FIELDS_JSON_SCHEMA,
    LEAD_FIELDS_TOOL,
    build_extraction_system_prompt,
    render_known_lead,
    result_from_fields,
)


def test_schema_has_core_fields():
    props = LEAD_FIELDS_JSON_SCHEMA["properties"]
    for field in ("name", "email", "phone", "city", "address", "average_energy_bill"):
        assert field in props


def test_tool_wraps_schema():
    assert LEAD_FIELDS_TOOL["name"] == "record_lead_fields"
    assert LEAD_FIELDS_TOOL["input_schema"] == LEAD_FIELDS_JSON_SCHEMA


def test_system_prompt_mentions_bare_answers():
    text = build_extraction_system_prompt()
    assert "histórico" in text.lower()
    assert "null" in text.lower()


def test_result_from_fields_builds_model():
    result = result_from_fields({"name": "Eduardo Freire Maia", "email": "a@b.com"})
    assert result.name == "Eduardo Freire Maia"
    assert result.email == "a@b.com"


def test_result_from_fields_rejects_invalid():
    with pytest.raises(ValueError):
        result_from_fields({"property_type": "spaceship"})


def test_render_known_lead_handles_none():
    assert render_known_lead(None) == "{}"
