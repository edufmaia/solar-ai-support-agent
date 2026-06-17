import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..schemas.agent_event import AgentEventCreate, AgentEventRead


class AgentEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: AgentEventCreate) -> AgentEventRead:
        query = text(
            """
            INSERT INTO agent_events (
                conversation_id,
                lead_id,
                event_type,
                event_source,
                payload
            )
            VALUES (
                :conversation_id,
                :lead_id,
                :event_type,
                :event_source,
                CAST(:payload AS JSONB)
            )
            RETURNING *
            """
        )
        params = data.model_dump()
        params["payload"] = json.dumps(data.payload, default=str)

        try:
            result = self.session.execute(query, params)
            row = result.mappings().one()
            self.session.commit()
            return AgentEventRead.model_validate(dict(row))
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def list_by_conversation_id(self, conversation_id: UUID) -> list[AgentEventRead]:
        query = text(
            """
            SELECT *
            FROM agent_events
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC
            """
        )
        result = self.session.execute(query, {"conversation_id": conversation_id})
        return [AgentEventRead.model_validate(dict(row)) for row in result.mappings().all()]

    def list_by_event_type(self, event_type: str) -> list[AgentEventRead]:
        query = text(
            """
            SELECT *
            FROM agent_events
            WHERE event_type = :event_type
            ORDER BY created_at DESC
            """
        )
        result = self.session.execute(query, {"event_type": event_type})
        return [AgentEventRead.model_validate(dict(row)) for row in result.mappings().all()]
