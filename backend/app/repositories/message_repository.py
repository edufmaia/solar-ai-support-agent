from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..schemas.message import MessageCreate, MessageRead


class MessageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: MessageCreate) -> MessageRead:
        query = text(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content,
                model_provider,
                model_name,
                input_tokens,
                output_tokens,
                estimated_cost
            )
            VALUES (
                :conversation_id,
                :role,
                :content,
                :model_provider,
                :model_name,
                :input_tokens,
                :output_tokens,
                :estimated_cost
            )
            RETURNING *
            """
        )
        try:
            result = self.session.execute(query, data.model_dump())
            row = result.mappings().one()
            self.session.commit()
            return MessageRead.model_validate(dict(row))
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def get_by_id(self, message_id: UUID) -> MessageRead | None:
        query = text(
            """
            SELECT *
            FROM messages
            WHERE id = :message_id
            """
        )
        result = self.session.execute(query, {"message_id": message_id})
        row = result.mappings().one_or_none()
        return MessageRead.model_validate(dict(row)) if row else None

    def list_by_conversation_id(self, conversation_id: UUID) -> list[MessageRead]:
        query = text(
            """
            SELECT *
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC
            """
        )
        result = self.session.execute(query, {"conversation_id": conversation_id})
        return [MessageRead.model_validate(dict(row)) for row in result.mappings().all()]
