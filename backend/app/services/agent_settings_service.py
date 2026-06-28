from sqlalchemy.orm import Session

from ..llm.context import build_response_instructions
from ..repositories.agent_settings_repository import AgentSettingsRepository
from ..schemas.agent_settings import AgentSettingsRead


class AgentSettingsService:
    def __init__(self, session: Session) -> None:
        self.repository = AgentSettingsRepository(session)

    def get(self) -> AgentSettingsRead:
        return self.repository.get()

    def effective_system_prompt(self) -> str:
        return build_response_instructions(self.repository.get().system_prompt)

    def is_custom(self) -> bool:
        prompt = self.repository.get().system_prompt
        return bool(prompt and prompt.strip())
