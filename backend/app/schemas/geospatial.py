from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GeospatialAnalysisCreate(BaseModel):
    lead_id: UUID
    conversation_id: UUID | None = None
    raw_address: str | None = None
    formatted_address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    address_confidence: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class GeospatialAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    conversation_id: UUID | None = None
    raw_address: str | None = None
    formatted_address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    address_confidence: str | None = None
    solar_data_available: bool
    estimated_panel_min: int | None = None
    estimated_panel_max: int | None = None
    estimated_system_kwp: Decimal | None = None
    confidence_level: str | None = None
    requires_technical_review: bool
    raw_response: dict[str, Any] | None = None
    created_at: datetime
