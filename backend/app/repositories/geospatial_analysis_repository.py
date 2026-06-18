import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..schemas.geospatial import GeospatialAnalysisCreate, GeospatialAnalysisRead


class GeospatialAnalysisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: GeospatialAnalysisCreate) -> GeospatialAnalysisRead:
        query = text(
            """
            INSERT INTO geospatial_analysis (
                lead_id,
                conversation_id,
                raw_address,
                formatted_address,
                latitude,
                longitude,
                address_confidence,
                raw_response
            )
            VALUES (
                :lead_id,
                :conversation_id,
                :raw_address,
                :formatted_address,
                :latitude,
                :longitude,
                :address_confidence,
                CAST(:raw_response AS JSONB)
            )
            RETURNING *
            """
        )
        params = data.model_dump()
        params["raw_response"] = json.dumps(data.raw_response, default=str)

        try:
            result = self.session.execute(query, params)
            row = result.mappings().one()
            self.session.commit()
            return GeospatialAnalysisRead.model_validate(dict(row))
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def exists_for_lead(self, lead_id: UUID) -> bool:
        query = text(
            """
            SELECT 1
            FROM geospatial_analysis
            WHERE lead_id = :lead_id
            LIMIT 1
            """
        )
        result = self.session.execute(query, {"lead_id": lead_id})
        return result.first() is not None

    def get_latest_by_lead_id(self, lead_id: UUID) -> GeospatialAnalysisRead | None:
        query = text(
            """
            SELECT *
            FROM geospatial_analysis
            WHERE lead_id = :lead_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        result = self.session.execute(query, {"lead_id": lead_id})
        row = result.mappings().one_or_none()
        return GeospatialAnalysisRead.model_validate(dict(row)) if row else None
