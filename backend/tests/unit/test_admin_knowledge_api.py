import io
from datetime import datetime
from uuid import uuid4

import pytest
from app.config.database import get_db_session
from app.main import create_app
from app.schemas.agent_settings import AgentSettingsRead
from app.schemas.knowledge import KnowledgeDocumentGroup
from app.security.admin_auth import require_admin
from fastapi.testclient import TestClient

GID = uuid4()


class _FakeSettingsService:
    def __init__(self, *_a, **_k):
        self.repository = self

    def effective_system_prompt(self):
        return "Prompt efetivo"

    def is_custom(self):
        return False

    def get(self):
        return AgentSettingsRead(
            system_prompt=None, knowledge_enabled=True, updated_at=datetime(2026, 1, 1)
        )

    def update(self, *_a, **_k): ...

    def reset_prompt(self): ...


class _FakeRepo:
    def __init__(self, *_a, **_k): ...

    def insert_chunks(self, *_a, **_k):
        return 2

    def list_groups(self):
        return [
            KnowledgeDocumentGroup(
                document_group_id=GID,
                title="Política",
                source="politica.txt",
                category="comercial",
                chunk_count=2,
                is_active=True,
                updated_at=datetime(2026, 1, 1),
            )
        ]

    def set_active(self, group_id, is_active):
        return 1 if group_id == GID else 0

    def delete_group(self, group_id):
        return 2 if group_id == GID else 0


@pytest.fixture
def client(monkeypatch):
    app = create_app()
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[get_db_session] = lambda: None

    def fake_ingest(**kwargs):
        from app.schemas.knowledge import KnowledgeIngestResult

        return ["chunk1", "chunk2"], KnowledgeIngestResult(
            document_group_id=uuid4(),
            chunk_count=2,
            source=kwargs.get("source"),
            truncated=False,
        )

    monkeypatch.setattr("app.api.admin.ingest", fake_ingest)
    monkeypatch.setattr("app.api.admin.KnowledgeDocumentRepository", _FakeRepo)
    monkeypatch.setattr("app.api.admin.AgentSettingsService", _FakeSettingsService)
    return TestClient(app)


def test_get_agent_settings(client):
    res = client.get("/admin/agent-settings")
    assert res.status_code == 200
    body = res.json()
    assert body["system_prompt"] == "Prompt efetivo"
    assert body["is_custom"] is False
    assert body["knowledge_enabled"] is True


def test_put_agent_settings(client):
    res = client.put(
        "/admin/agent-settings", json={"system_prompt": "Novo", "knowledge_enabled": False}
    )
    assert res.status_code == 200


def test_reset_agent_settings(client):
    assert client.post("/admin/agent-settings/reset").status_code == 200


def test_list_knowledge(client):
    res = client.get("/admin/knowledge")
    assert res.status_code == 200
    assert res.json()[0]["chunk_count"] == 2


def test_upload_text_returns_ingest_result(client):
    res = client.post(
        "/admin/knowledge",
        data={"title": "Política", "category": "comercial", "text": "garantia 25 anos"},
    )
    assert res.status_code == 201
    assert res.json()["chunk_count"] == 2


def test_upload_file_returns_ingest_result(client):
    res = client.post(
        "/admin/knowledge",
        data={"title": "Preços"},
        files={"file": ("precos.txt", io.BytesIO(b"tabela de precos"), "text/plain")},
    )
    assert res.status_code == 201


def test_patch_knowledge_active(client):
    assert client.patch(f"/admin/knowledge/{GID}?is_active=false").status_code == 200


def test_patch_knowledge_not_found(client):
    assert client.patch(f"/admin/knowledge/{uuid4()}?is_active=false").status_code == 404


def test_delete_knowledge(client):
    assert client.delete(f"/admin/knowledge/{GID}").status_code == 204


def test_delete_knowledge_not_found(client):
    assert client.delete(f"/admin/knowledge/{uuid4()}").status_code == 404
