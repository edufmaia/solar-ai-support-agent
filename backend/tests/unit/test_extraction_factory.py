import pytest
from app.config.settings import Settings
from app.llm.base import LLMProviderConfigurationError
from app.llm.extraction.claude_extractor import ClaudeFieldExtractor
from app.llm.extraction.factory import build_lead_extraction_provider
from app.llm.extraction.openai_extractor import OpenAIFieldExtractor


def test_explicit_openai():
    p = build_lead_extraction_provider(
        Settings(lead_extraction_provider="openai", openai_api_key="k")
    )
    assert isinstance(p, OpenAIFieldExtractor)


def test_explicit_claude():
    p = build_lead_extraction_provider(
        Settings(lead_extraction_provider="claude", anthropic_api_key="k")
    )
    assert isinstance(p, ClaudeFieldExtractor)


def test_regex_disables_llm():
    assert build_lead_extraction_provider(Settings(lead_extraction_provider="regex")) is None


def test_auto_follows_hybrid_real_provider():
    s = Settings(
        lead_extraction_provider="auto",
        llm_provider="hybrid",
        hybrid_real_provider="claude",
        anthropic_api_key="k",
    )
    assert isinstance(build_lead_extraction_provider(s), ClaudeFieldExtractor)


def test_auto_mock_disables_llm():
    assert (
        build_lead_extraction_provider(
            Settings(lead_extraction_provider="auto", llm_provider="mock")
        )
        is None
    )


def test_unsupported_value_raises():
    with pytest.raises(LLMProviderConfigurationError):
        build_lead_extraction_provider(Settings(lead_extraction_provider="banana"))
