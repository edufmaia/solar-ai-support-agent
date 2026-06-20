from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..schemas.conversation import ConversationCreate, ConversationRead
from ..schemas.metrics import ConversationMetrics


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: ConversationCreate) -> ConversationRead:
        query = text(
            """
            INSERT INTO conversations (
                lead_id,
                channel,
                status,
                current_state,
                assigned_to_human
            )
            VALUES (
                :lead_id,
                :channel,
                :status,
                :current_state,
                :assigned_to_human
            )
            RETURNING *
            """
        )
        try:
            result = self.session.execute(query, data.model_dump())
            row = result.mappings().one()
            self.session.commit()
            return ConversationRead.model_validate(dict(row))
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def get_by_id(self, conversation_id: UUID) -> ConversationRead | None:
        query = text(
            """
            SELECT *
            FROM conversations
            WHERE id = :conversation_id
            """
        )
        result = self.session.execute(query, {"conversation_id": conversation_id})
        row = result.mappings().one_or_none()
        return ConversationRead.model_validate(dict(row)) if row else None

    def get_by_lead_id(self, lead_id: UUID) -> list[ConversationRead]:
        query = text(
            """
            SELECT *
            FROM conversations
            WHERE lead_id = :lead_id
            ORDER BY started_at DESC
            """
        )
        result = self.session.execute(query, {"lead_id": lead_id})
        return [ConversationRead.model_validate(dict(row)) for row in result.mappings().all()]

    def update_state(self, conversation_id: UUID, current_state: str) -> ConversationRead | None:
        query = text(
            """
            UPDATE conversations
            SET
                current_state = :current_state,
                updated_at = now()
            WHERE id = :conversation_id
            RETURNING *
            """
        )
        try:
            result = self.session.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "current_state": current_state,
                },
            )
            row = result.mappings().one_or_none()
            self.session.commit()
            return ConversationRead.model_validate(dict(row)) if row else None
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def close(self, conversation_id: UUID) -> ConversationRead | None:
        query = text(
            """
            UPDATE conversations
            SET
                status = 'closed',
                closed_at = now(),
                updated_at = now()
            WHERE id = :conversation_id
            RETURNING *
            """
        )
        try:
            result = self.session.execute(query, {"conversation_id": conversation_id})
            row = result.mappings().one_or_none()
            self.session.commit()
            return ConversationRead.model_validate(dict(row)) if row else None
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def assign_lead(self, conversation_id: UUID, lead_id: UUID) -> ConversationRead | None:
        query = text(
            """
            UPDATE conversations
            SET
                lead_id = :lead_id,
                updated_at = now()
            WHERE id = :conversation_id
            RETURNING *
            """
        )
        try:
            result = self.session.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "lead_id": lead_id,
                },
            )
            row = result.mappings().one_or_none()
            self.session.commit()
            return ConversationRead.model_validate(dict(row)) if row else None
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def metrics(self) -> ConversationMetrics:
        """Aggregate conversation counts: total and how many are with a human."""
        row = self.session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE assigned_to_human) AS assigned_to_human
                FROM conversations
                """
            )
        ).mappings().one()
        return ConversationMetrics(
            total=row["total"],
            assigned_to_human=row["assigned_to_human"],
        )

    def mark_handoff(self, conversation_id: UUID) -> ConversationRead | None:
        query = text(
            """
            UPDATE conversations
            SET
                assigned_to_human = TRUE,
                status = 'waiting_human',
                updated_at = now()
            WHERE id = :conversation_id
            RETURNING *
            """
        )
        try:
            result = self.session.execute(query, {"conversation_id": conversation_id})
            row = result.mappings().one_or_none()
            self.session.commit()
            return ConversationRead.model_validate(dict(row)) if row else None
        except SQLAlchemyError:
            self.session.rollback()
            raise
