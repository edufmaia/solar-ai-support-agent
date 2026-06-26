import pytest

from app.config.settings import Settings
from app.llm.base import LLMProviderConfigurationError, LLMProviderInvocationError
from app.llm.extraction.claude_extractor import ClaudeFieldExtractor


class _FakeToolUse:
    def __init__(self, data):
        self.type = "tool_use"
        self.name = "record_lead_fields"
        self.input = data


class _FakeMessage:
    def __init__(self, blocks):
        self.content = blocks


class _FakeMessages:
    def __init__(self, message):
        self._message = message
        self.captured_kwargs = None

    def create(self, **kwargs):
        self.captured_kwargs = kwargs
        return self._message


class _FakeClient:
    def __init__(self, message):
        self.messages = _FakeMessages(message)


def _settings(**kw):
    base = dict(anthropic_api_key="k", lead_extraction_model="claude-haiku-4-5")
    base.update(kw)
    return Settings(**base)


def test_extracts_fields_from_tool_use():
    msg = _FakeMessage([_FakeToolUse({"name": "Eduardo Freire Maia", "email": "a@b.com",
                                      "intent": "solar_interest", "has_solar_interest": True,
                                      "wants_human": False, "geo_consent": False})])
    extractor = ClaudeFieldExtractor(settings=_settings(), client=_FakeClient(msg))
    result = extractor.extract_fields(
        history=[{"role": "assistant", "content": "Qual seu e-mail?"},
                 {"role": "user", "content": "contato.eduardofmaia@gmail.com"}],
        known_lead=None,
    )
    assert result.name == "Eduardo Freire Maia"
    assert result.email == "a@b.com"
    assert extractor.client.messages.captured_kwargs["tool_choice"]["name"] == "record_lead_fields"


def test_no_tool_use_block_raises():
    class _Text:
        type = "text"
        text = "oi"
    extractor = ClaudeFieldExtractor(settings=_settings(), client=_FakeClient(_FakeMessage([_Text()])))
    with pytest.raises(LLMProviderInvocationError):
        extractor.extract_fields(history=[], known_lead=None)


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(LLMProviderConfigurationError):
        ClaudeFieldExtractor(settings=Settings(anthropic_api_key=None))
