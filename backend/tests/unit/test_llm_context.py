from app.llm.context import geospatial_prompt_section


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
