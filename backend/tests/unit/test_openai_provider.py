from uuid import uuid4

from app.config.settings import Settings
from app.llm.openai_provider import OpenAIProvider
from app.schemas.llm import LLMRequest


class _FakeUsage:
    def __init__(self, i, o):
        self.input_tokens = i
        self.output_tokens = o


class _FakeResponse:
    def __init__(self):
        self.output_text = "ok"
        self.usage = _FakeUsage(10, 5)
        self.model = "gpt-4o-mini"
        self.id = "resp_test"
        self.status = "completed"


class _FakeResponses:
    def __init__(self):
        self.captured_kwargs = None

    def create(self, **kwargs):
        self.captured_kwargs = kwargs
        return _FakeResponse()


class _FakeClient:
    def __init__(self):
        self.responses = _FakeResponses()


def _settings():
    return Settings(openai_api_key="test-key", openai_model="gpt-4o-mini")


def test_openai_uses_history_input_and_hardened_prompt():
    client = _FakeClient()
    provider = OpenAIProvider(settings=_settings(), client=client)
    req = LLMRequest(
        conversation_id=uuid4(),
        user_message="Eduardo Freire Maia",
        history=[
            {"role": "assistant", "content": "Qual seu nome?"},
            {"role": "user", "content": "Eduardo Freire Maia"},
        ],
    )
    provider.generate_response(req)
    kwargs = client.responses.captured_kwargs
    assert isinstance(kwargs["input"], list)
    assert kwargs["input"][0]["content"] == "Qual seu nome?"
    assert "[Seu Nome]" in kwargs["instructions"]


def test_openai_falls_back_to_current_message_without_history():
    client = _FakeClient()
    provider = OpenAIProvider(settings=_settings(), client=client)
    req = LLMRequest(conversation_id=uuid4(), user_message="olá")
    provider.generate_response(req)
    kwargs = client.responses.captured_kwargs
    assert kwargs["input"] == [{"role": "user", "content": "olá"}]
