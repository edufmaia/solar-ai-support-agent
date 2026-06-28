from datetime import datetime

from app.llm.context import DEFAULT_RESPONSE_INSTRUCTIONS
from app.schemas.agent_settings import AgentSettingsRead
from app.services.agent_settings_service import AgentSettingsService


class _StubRepo:
    def __init__(self, prompt):
        self._row = AgentSettingsRead(
            system_prompt=prompt, knowledge_enabled=True, updated_at=datetime(2026, 1, 1)
        )

    def get(self):
        return self._row


def _service(prompt):
    svc = object.__new__(AgentSettingsService)
    svc.repository = _StubRepo(prompt)
    return svc


def test_effective_prompt_falls_back_to_default():
    assert _service(None).effective_system_prompt() == DEFAULT_RESPONSE_INSTRUCTIONS
    assert _service(None).is_custom() is False


def test_effective_prompt_uses_custom():
    svc = _service("Prompt da empresa")
    assert svc.effective_system_prompt() == "Prompt da empresa"
    assert svc.is_custom() is True
