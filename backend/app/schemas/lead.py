from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

LeadTemperature = Literal["cold", "warm", "hot"]


class LeadCreate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    city: str | None = None
    state: str | None = None
    address: str | None = None
    property_type: str | None = None
    average_energy_bill: Decimal | None = None
    intent: str | None = None
    source_channel: str | None = None


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    city: str | None = None
    state: str | None = None
    address: str | None = None
    property_type: str | None = None
    average_energy_bill: Decimal | None = None
    intent: str | None = None
    lead_score: int | None = None
    lead_temperature: LeadTemperature | None = None
    status: str | None = None
    source_channel: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadScoreUpdate(BaseModel):
    lead_score: int
    lead_temperature: LeadTemperature
