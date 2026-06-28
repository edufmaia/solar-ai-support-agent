from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..schemas.agent_settings import AgentSettingsRead


class AgentSettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self) -> AgentSettingsRead:
        row = (
            self.session.execute(
                text(
                    "SELECT system_prompt, knowledge_enabled, updated_at "
                    "FROM agent_settings WHERE id = 1"
                )
            )
            .mappings()
            .one()
        )
        return AgentSettingsRead.model_validate(dict(row))

    def update(
        self, system_prompt: str | None, knowledge_enabled: bool | None
    ) -> AgentSettingsRead:
        try:
            self.session.execute(
                text(
                    "UPDATE agent_settings SET "
                    "system_prompt = COALESCE(:system_prompt, system_prompt), "
                    "knowledge_enabled = COALESCE(:knowledge_enabled, knowledge_enabled), "
                    "updated_at = now() WHERE id = 1"
                ),
                {"system_prompt": system_prompt, "knowledge_enabled": knowledge_enabled},
            )
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        return self.get()

    def reset_prompt(self) -> AgentSettingsRead:
        try:
            self.session.execute(
                text(
                    "UPDATE agent_settings SET system_prompt = NULL, "
                    "updated_at = now() WHERE id = 1"
                )
            )
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        return self.get()
