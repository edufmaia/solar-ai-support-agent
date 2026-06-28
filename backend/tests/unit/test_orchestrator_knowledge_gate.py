from app.agents.orchestrator import MockAgentOrchestrator


class _Provider:
    def __init__(self, name):
        self.provider_name = name


class _RetrievalSpy:
    def __init__(self):
        self.calls = 0

    def retrieve(self, _q):
        self.calls += 1
        return [{"content": "x", "source": "s"}]


def _orch(provider_name, enabled):
    o = object.__new__(MockAgentOrchestrator)
    o.llm_provider = _Provider(provider_name)
    o._kb_enabled = enabled
    o._retrieval = _RetrievalSpy()
    return o


def test_mock_provider_skips_retrieval():
    o = _orch("mock", True)
    snippets = o._retrieve_knowledge("quero energia solar")
    assert snippets == []
    assert o._retrieval.calls == 0


def test_real_provider_retrieves_when_enabled():
    o = _orch("openai", True)
    snippets = o._retrieve_knowledge("quero energia solar")
    assert len(snippets) == 1
    assert o._retrieval.calls == 1


def test_disabled_knowledge_skips_retrieval():
    o = _orch("openai", False)
    assert o._retrieve_knowledge("x") == []
    assert o._retrieval.calls == 0
