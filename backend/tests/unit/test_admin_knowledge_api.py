import io
from uuid import uuid4

import pytest
from app.main import create_app
from app.security.admin_auth import require_admin
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    app = create_app()
    app.dependency_overrides[require_admin] = lambda: None

    def fake_ingest(**kwargs):
        from app.schemas.knowledge import KnowledgeIngestResult

        return ["chunk1", "chunk2"], KnowledgeIngestResult(
            document_group_id=uuid4(),
            chunk_count=2,
            source=kwargs.get("source"),
            truncated=False,
        )

    monkeypatch.setattr("app.api.admin.ingest", fake_ingest)

    class _Repo:
        def __init__(self, *_a, **_k): ...

        def insert_chunks(self, *_a, **_k):
            return 2

    monkeypatch.setattr("app.api.admin.KnowledgeDocumentRepository", _Repo)
    return TestClient(app)


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
