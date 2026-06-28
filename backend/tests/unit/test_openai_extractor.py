import json

import pytest
from app.config.settings import Settings
from app.llm.base import LLMProviderConfigurationError, LLMProviderInvocationError
from app.llm.extraction.openai_extractor import OpenAIFieldExtractor


class _FakeResponse:
    def __init__(self, text):
        self.output_text = text


class _FakeResponses:
    def __init__(self, text):
        self._text = text
        self.captured_kwargs = None

    def create(self, **kwargs):
        self.captured_kwargs = kwargs
        return _FakeResponse(self._text)


class _FakeClient:
    def __init__(self, text):
        self.responses = _FakeResponses(text)


def _settings(**kw):
    base = dict(openai_api_key="k", lead_extraction_model="gpt-4o-mini")
    base.update(kw)
    return Settings(**base)


def test_extracts_name_and_email_from_history():
    payload = json.dumps(
        {
            "name": "Eduardo Freire Maia",
            "email": "a@b.com",
            "intent": "solar_interest",
            "has_solar_interest": True,
            "wants_human": False,
            "geo_consent": False,
        }
    )
    extractor = OpenAIFieldExtractor(settings=_settings(), client=_FakeClient(payload))
    result = extractor.extract_fields(
        history=[
            {"role": "assistant", "content": "Qual seu nome?"},
            {"role": "user", "content": "Eduardo Freire Maia"},
        ],
        known_lead={"city": "Mossoró"},
    )
    assert result.name == "Eduardo Freire Maia"
    assert result.email == "a@b.com"


def test_invalid_json_raises_invocation_error():
    extractor = OpenAIFieldExtractor(settings=_settings(), client=_FakeClient("not json"))
    with pytest.raises(LLMProviderInvocationError):
        extractor.extract_fields(history=[], known_lead=None)


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(LLMProviderConfigurationError):
        OpenAIFieldExtractor(settings=Settings(openai_api_key=None))
