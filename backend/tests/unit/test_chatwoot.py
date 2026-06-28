from uuid import uuid4

import httpx
import pytest
from app.config.settings import Settings
from app.integrations.chatwoot.client import (
    ChatwootClient,
    ChatwootConfigurationError,
    ChatwootError,
)
from app.schemas.chat import ChatResponse
from app.schemas.chatwoot import ChatwootRef, ChatwootWebhookEvent
from app.services.chatwoot_webhook_service import ChatwootWebhookService


class _Resp:
    def raise_for_status(self) -> None:
        return None


class _CapturingHttp:
    def __init__(self, raise_exc=None):
        self.calls = []
        self.raise_exc = raise_exc

    def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.raise_exc:
            raise self.raise_exc
        return _Resp()


def _settings(**overrides) -> Settings:
    base = dict(chatwoot_base_url="https://cw.example.com", chatwoot_api_access_token="tok")
    base.update(overrides)
    return Settings(**base)


# --- ChatwootClient ---------------------------------------------------------


def test_send_message_builds_request():
    http = _CapturingHttp()
    client = ChatwootClient(settings=_settings(), client=http)
    client.send_message(7, 42, "Olá")
    call = http.calls[0]
    assert call["url"] == "https://cw.example.com/api/v1/accounts/7/conversations/42/messages"
    assert call["headers"] == {"api_access_token": "tok"}
    assert call["json"] == {"content": "Olá", "message_type": "outgoing"}


def test_send_message_requires_config():
    client = ChatwootClient(
        settings=_settings(chatwoot_base_url=None, chatwoot_api_access_token=None)
    )
    with pytest.raises(ChatwootConfigurationError):
        client.send_message(1, 1, "x")


def test_send_message_wraps_http_error():
    http = _CapturingHttp(raise_exc=httpx.HTTPError("boom"))
    client = ChatwootClient(settings=_settings(), client=http)
    with pytest.raises(ChatwootError):
        client.send_message(1, 1, "x")


# --- ChatwootWebhookService fakes ------------------------------------------


class _FakeOrchestrator:
    def __init__(self):
        self.requests = []
        self.conversation_id = uuid4()

    def handle_chat(self, payload):
        self.requests.append(payload)
        return ChatResponse(conversation_id=self.conversation_id, response="resposta", mode="mock")


class _FakeClient:
    def __init__(self, raise_exc=None):
        self.sent = []
        self.raise_exc = raise_exc

    def send_message(self, account_id, conversation_id, content):
        if self.raise_exc:
            raise self.raise_exc
        self.sent.append((account_id, conversation_id, content))


class _FakeMap:
    def __init__(self, mapped=None):
        self.mapped = mapped
        self.saved = []

    def get(self, account_id, cw_conversation_id):
        return self.mapped

    def set(self, account_id, cw_conversation_id, conversation_id):
        self.saved.append((account_id, cw_conversation_id, conversation_id))


def _event(event="message_created", message_type="incoming", content="Oi", conv=10, acc=3):
    return ChatwootWebhookEvent(
        event=event,
        message_type=message_type,
        content=content,
        conversation=ChatwootRef(id=conv) if conv is not None else None,
        account=ChatwootRef(id=acc) if acc is not None else None,
    )


def _service(orchestrator, client, conversation_map):
    return ChatwootWebhookService(
        None, orchestrator=orchestrator, client=client, conversation_map=conversation_map
    )


def test_ignores_non_message_event():
    out = _service(_FakeOrchestrator(), _FakeClient(), _FakeMap()).handle(
        _event(event="conversation_created")
    )
    assert out == {"status": "ignored", "reason": "event"}


def test_ignores_outgoing_message():
    out = _service(_FakeOrchestrator(), _FakeClient(), _FakeMap()).handle(
        _event(message_type="outgoing")
    )
    assert out["status"] == "ignored" and out["reason"] == "message_type"


def test_ignores_empty_content():
    out = _service(_FakeOrchestrator(), _FakeClient(), _FakeMap()).handle(_event(content="   "))
    assert out["status"] == "ignored" and out["reason"] == "empty_content"


def test_handles_incoming_and_replies():
    orch, client, cmap = _FakeOrchestrator(), _FakeClient(), _FakeMap()
    out = _service(orch, client, cmap).handle(_event())
    assert out["status"] == "handled"
    assert out["reply_sent"] is True
    assert orch.requests[0].channel == "chatwoot"
    assert orch.requests[0].message == "Oi"
    assert client.sent[0] == (3, 10, "resposta")
    assert cmap.saved[0] == (3, 10, orch.conversation_id)


def test_reply_failure_still_acks():
    client = _FakeClient(raise_exc=ChatwootError("down"))
    out = _service(_FakeOrchestrator(), client, _FakeMap()).handle(_event())
    assert out["status"] == "handled"
    assert out["reply_sent"] is False
    assert "reply_error" in out
