from app.config.settings import Settings


def test_extraction_settings_defaults():
    s = Settings()
    assert s.lead_extraction_provider == "auto"
    assert s.lead_extraction_model is None
    assert s.lead_extraction_max_tokens == 1024


def test_extraction_settings_override():
    s = Settings(lead_extraction_provider="claude", lead_extraction_model="claude-haiku-4-5")
    assert s.lead_extraction_provider == "claude"
    assert s.lead_extraction_model == "claude-haiku-4-5"
