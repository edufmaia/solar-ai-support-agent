from app.services.knowledge_retrieval_service import KnowledgeRetrievalService


class _StubRepo:
    def __init__(self):
        self.args = None

    def search(self, query, limit, min_rank):
        self.args = (query, limit, min_rank)
        return [{"content": "x", "source": "s"}]


class _Settings:
    knowledge_top_k = 4
    knowledge_min_rank = 0.01


def _service():
    svc = object.__new__(KnowledgeRetrievalService)
    svc.repository = _StubRepo()
    svc.settings = _Settings()
    return svc


def test_empty_query_returns_no_snippets():
    svc = _service()
    assert svc.retrieve("") == []
    assert svc.retrieve("   ") == []
    assert svc.repository.args is None


def test_retrieve_delegates_with_settings():
    svc = _service()
    result = svc.retrieve("garantia dos painéis")
    assert result == [{"content": "x", "source": "s"}]
    assert svc.repository.args == ("garantia dos painéis", 4, 0.01)
