from decimal import Decimal
from uuid import uuid4

import pytest
from app.config.settings import Settings
from app.llm.base import LLMProviderConfigurationError, LLMProviderInvocationError
from app.llm.claude_provider import ClaudeProvider
from app.schemas.llm import LLMRequest


class _FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeMessage:
    def __init__(self, content, usage, model):
        self.content = content
        self.usage = usage
        self.model = model
        self.id = "msg_test"
        self.stop_reason = "end_turn"


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


def _settings(**overrides):
    base = {
        "anthropic_api_key": "test-key",
        "claude_model": "claude-opus-4-8",
        "claude_max_tokens": 1024,
        "claude_input_price_per_1m_tokens": Decimal("5.00"),
        "claude_output_price_per_1m_tokens": Decimal("25.00"),
    }
    base.update(overrides)
    return Settings(**base)


def _request():
    return LLMRequest(
        conversation_id=uuid4(),
        user_message="Tenho interesse em energia solar.",
        current_state="new_lead",
        lead_data={"city": "Natal"},
        lead_score=70,
        lead_temperature="hot",
        extracted_data={"city": "Natal", "intent": "solar_interest"},
    )


def test_generate_response_maps_content_usage_and_cost():
    message = _FakeMessage(
        content=[_FakeTextBlock("Olá! Posso te ajudar com energia solar.")],
        usage=_FakeUsage(input_tokens=100, output_tokens=50),
        model="claude-opus-4-8",
    )
    client = _FakeClient(message)
    provider = ClaudeProvider(settings=_settings(), client=client)

    response = provider.generate_response(_request())

    assert response.content == "Olá! Posso te ajudar com energia solar."
    assert response.provider == "claude"
    assert response.model_name == "claude-opus-4-8"
    assert response.input_tokens == 100
    assert response.output_tokens == 50
    # 100/1e6 * 5 + 50/1e6 * 25 = 0.0005 + 0.00125 = 0.00175
    assert response.estimated_cost == Decimal("0.001750")
    assert client.messages.captured_kwargs["model"] == "claude-opus-4-8"
    assert client.messages.captured_kwargs["max_tokens"] == 1024
    assert client.messages.captured_kwargs["messages"][0]["role"] == "user"
    assert isinstance(client.messages.captured_kwargs["system"], str)


def test_claude_uses_history_messages_and_hardened_prompt():
    message = _FakeMessage([_FakeTextBlock("ok")], _FakeUsage(10, 5), "claude-haiku-4-5")
    client = _FakeClient(message)
    provider = ClaudeProvider(settings=_settings(), client=client)
    req = _request()
    req.history = [
        {"role": "assistant", "content": "Qual seu nome?"},
        {"role": "user", "content": "Eduardo Freire Maia"},
    ]
    provider.generate_response(req)
    kwargs = client.messages.captured_kwargs
    assert kwargs["messages"][0]["content"] == "Qual seu nome?"
    assert kwargs["messages"][-1]["content"] == "Eduardo Freire Maia"
    assert "[Seu Nome]" in kwargs["system"]


def test_event_type_and_source_follow_base_contract():
    provider = ClaudeProvider(
        settings=_settings(),
        client=_FakeClient(_FakeMessage([], _FakeUsage(0, 0), "claude-opus-4-8")),
    )

    assert provider.provider_name == "claude"
    assert provider.event_source == "claude_provider"
    assert provider.event_type == "llm_claude_response_generated"


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(LLMProviderConfigurationError):
        ClaudeProvider(settings=_settings(anthropic_api_key=None))


def test_empty_text_output_raises_invocation_error():
    message = _FakeMessage(content=[], usage=_FakeUsage(10, 0), model="claude-opus-4-8")
    provider = ClaudeProvider(settings=_settings(), client=_FakeClient(message))

    with pytest.raises(LLMProviderInvocationError):
        provider.generate_response(_request())


def test_factory_builds_claude_provider_for_claude_setting():
    from app.llm.factory import build_llm_provider

    provider = build_llm_provider(settings=_settings(llm_provider="claude"))

    assert isinstance(provider, ClaudeProvider)
    assert provider.provider_name == "claude"


def test_api_error_raises_invocation_error():
    import httpx
    from anthropic import APIConnectionError

    class _ErrorMessages:
        def create(self, **_kwargs):
            raise APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))

    class _ErrorClient:
        messages = _ErrorMessages()

    provider = ClaudeProvider(settings=_settings(), client=_ErrorClient())

    with pytest.raises(LLMProviderInvocationError, match="Anthropic Messages API request failed"):
        provider.generate_response(_request())
