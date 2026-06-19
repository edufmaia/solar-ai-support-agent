import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..schemas.geospatial import GeospatialAnalysisCreate, GeospatialAnalysisRead
from ..schemas.solar import SolarPotentialResult


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

    def update_solar_data(
        self, analysis_id: UUID, result: SolarPotentialResult
    ) -> GeospatialAnalysisRead | None:
        query = text(
            """
            UPDATE geospatial_analysis
            SET solar_data_available = :solar_data_available,
                estimated_panel_min = :estimated_panel_min,
                estimated_panel_max = :estimated_panel_max,
                estimated_system_kwp = :estimated_system_kwp,
                confidence_level = :confidence_level,
                requires_technical_review = :requires_technical_review,
                raw_response = COALESCE(raw_response, '{}'::jsonb)
                    || CAST(:raw_response AS JSONB)
            WHERE id = :analysis_id
            RETURNING *
            """
        )
        params = {
            "analysis_id": analysis_id,
            "solar_data_available": result.solar_data_available,
            "estimated_panel_min": result.estimated_panel_min,
            "estimated_panel_max": result.estimated_panel_max,
            "estimated_system_kwp": result.estimated_system_kwp,
            "confidence_level": result.confidence_level,
            "requires_technical_review": result.requires_technical_review,
            "raw_response": json.dumps({"solar": result.raw_response}, default=str),
        }

        try:
            db_result = self.session.execute(query, params)
            row = db_result.mappings().one_or_none()
            self.session.commit()
            return GeospatialAnalysisRead.model_validate(dict(row)) if row else None
        except SQLAlchemyError:
            self.session.rollback()
            raise
