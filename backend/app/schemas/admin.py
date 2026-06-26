from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from .lead import LeadTemperature


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


class ConversationListItem(BaseModel):
    conversation_id: UUID
    started_at: datetime
    channel: str | None = None
    status: str | None = None
    assigned_to_human: bool
    lead_id: UUID | None = None
    lead_name: str | None = None
    lead_city: str | None = None
    average_energy_bill: Decimal | None = None
    lead_score: int | None = None
    lead_temperature: LeadTemperature | None = None


class ConversationListResponse(BaseModel):
    items: list[ConversationListItem]
    total: int
    limit: int
    offset: int
