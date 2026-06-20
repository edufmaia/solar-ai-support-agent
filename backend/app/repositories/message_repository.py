from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..schemas.message import MessageCreate, MessageRead
from ..schemas.usage import UsageAggregate, UsageByModel


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

    def aggregate_usage(self, conversation_id: UUID | None = None) -> UsageAggregate:
        """Aggregate token usage and estimated cost recorded on messages.

        Source of truth for agent cost. Filters by conversation when given,
        otherwise aggregates globally. Read-only (no commit). Per-model
        breakdown ignores user messages (model_name IS NULL).
        """
        where = "WHERE conversation_id = :conversation_id" if conversation_id is not None else ""
        params = {"conversation_id": conversation_id} if conversation_id is not None else {}

        totals_query = text(
            f"""
            SELECT
                COUNT(*) AS total_messages,
                COALESCE(SUM(input_tokens), 0) AS total_input_tokens,
                COALESCE(SUM(output_tokens), 0) AS total_output_tokens,
                COALESCE(SUM(estimated_cost), 0) AS total_estimated_cost
            FROM messages
            {where}
            """
        )
        totals = self.session.execute(totals_query, params).mappings().one()

        model_where = "model_name IS NOT NULL"
        if conversation_id is not None:
            model_where = "conversation_id = :conversation_id AND " + model_where
        by_model_query = text(
            f"""
            SELECT
                model_provider,
                model_name,
                COUNT(*) AS message_count,
                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                COALESCE(SUM(estimated_cost), 0) AS estimated_cost
            FROM messages
            WHERE {model_where}
            GROUP BY model_provider, model_name
            ORDER BY model_provider, model_name
            """
        )
        by_model_rows = self.session.execute(by_model_query, params).mappings().all()

        return UsageAggregate(
            total_messages=totals["total_messages"],
            total_input_tokens=totals["total_input_tokens"],
            total_output_tokens=totals["total_output_tokens"],
            total_estimated_cost=totals["total_estimated_cost"],
            by_model=[UsageByModel.model_validate(dict(row)) for row in by_model_rows],
        )
