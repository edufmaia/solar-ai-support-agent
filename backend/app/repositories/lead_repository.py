from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..schemas.lead import LeadCreate, LeadRead, LeadScoreUpdate
from ..schemas.lead_scoring import LeadTemperature
from ..schemas.metrics import LeadMetrics


class LeadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: LeadCreate) -> LeadRead:
        query = text(
            """
            INSERT INTO leads (
                name,
                phone,
                email,
                city,
                state,
                address,
                property_type,
                average_energy_bill,
                intent,
                source_channel
            )
            VALUES (
                :name,
                :phone,
                :email,
                :city,
                :state,
                :address,
                :property_type,
                :average_energy_bill,
                :intent,
                :source_channel
            )
            RETURNING *
            """
        )
        try:
            result = self.session.execute(query, data.model_dump())
            row = result.mappings().one()
            self.session.commit()
            return LeadRead.model_validate(dict(row))
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def get_by_id(self, lead_id: UUID) -> LeadRead | None:
        query = text(
            """
            SELECT *
            FROM leads
            WHERE id = :lead_id
            """
        )
        result = self.session.execute(query, {"lead_id": lead_id})
        row = result.mappings().one_or_none()
        return LeadRead.model_validate(dict(row)) if row else None

    def get_by_phone(self, phone: str) -> LeadRead | None:
        query = text(
            """
            SELECT *
            FROM leads
            WHERE phone = :phone
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        result = self.session.execute(query, {"phone": phone})
        row = result.mappings().one_or_none()
        return LeadRead.model_validate(dict(row)) if row else None

    def update_score(
        self,
        lead_id: UUID,
        lead_score: int,
        lead_temperature: LeadTemperature,
    ) -> LeadRead | None:
        payload = LeadScoreUpdate(
            lead_score=lead_score,
            lead_temperature=lead_temperature,
        )
        query = text(
            """
            UPDATE leads
            SET
                lead_score = :lead_score,
                lead_temperature = :lead_temperature,
                updated_at = now()
            WHERE id = :lead_id
            RETURNING *
            """
        )
        try:
            result = self.session.execute(
                query,
                {
                    "lead_id": lead_id,
                    "lead_score": payload.lead_score,
                    "lead_temperature": payload.lead_temperature,
                },
            )
            row = result.mappings().one_or_none()
            self.session.commit()
            return LeadRead.model_validate(dict(row)) if row else None
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def update_basic_info(self, lead_id: UUID, data: LeadCreate) -> LeadRead | None:
        query = text(
            """
            UPDATE leads
            SET
                name = COALESCE(:name, name),
                phone = COALESCE(:phone, phone),
                email = COALESCE(:email, email),
                city = COALESCE(:city, city),
                state = COALESCE(:state, state),
                address = COALESCE(:address, address),
                property_type = COALESCE(:property_type, property_type),
                average_energy_bill = COALESCE(:average_energy_bill, average_energy_bill),
                intent = COALESCE(:intent, intent),
                source_channel = COALESCE(:source_channel, source_channel),
                updated_at = now()
            WHERE id = :lead_id
            RETURNING *
            """
        )

        params = data.model_dump()
        params["lead_id"] = lead_id

        try:
            result = self.session.execute(query, params)
            row = result.mappings().one_or_none()
            self.session.commit()
            return LeadRead.model_validate(dict(row)) if row else None
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def metrics(self) -> LeadMetrics:
        """Aggregate lead counts: total and breakdown by temperature."""
        total = self.session.execute(text("SELECT COUNT(*) FROM leads")).scalar_one()
        rows = (
            self.session.execute(
                text(
                    """
                SELECT COALESCE(lead_temperature, 'unscored') AS temperature, COUNT(*) AS count
                FROM leads
                GROUP BY COALESCE(lead_temperature, 'unscored')
                """
                )
            )
            .mappings()
            .all()
        )
        by_temperature = {row["temperature"]: row["count"] for row in rows}
        return LeadMetrics(total=total, by_temperature=by_temperature)

    def update_status(self, lead_id: UUID, status: str) -> LeadRead | None:
        query = text(
            """
            UPDATE leads
            SET
                status = :status,
                updated_at = now()
            WHERE id = :lead_id
            RETURNING *
            """
        )
        try:
            result = self.session.execute(
                query,
                {"lead_id": lead_id, "status": status},
            )
            row = result.mappings().one_or_none()
            self.session.commit()
            return LeadRead.model_validate(dict(row)) if row else None
        except SQLAlchemyError:
            self.session.rollback()
            raise
