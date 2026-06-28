from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from .lead_scoring import LeadIntent, PropertyType

HandoffReason = Literal[
    "user_requested",
    "hot_lead",
    "technical_review",
    "analysis_complete_with_contact",
]


class SaveLeadInput(BaseModel):
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


class UpdateLeadInput(SaveLeadInput):
    lead_id: UUID


class ClassifyLeadInput(BaseModel):
    lead_id: UUID
    name: str | None = None
    city: str | None = None
    average_energy_bill: Decimal | None = None
    property_type: PropertyType | None = None
    intent: LeadIntent | None = None
    has_solar_interest: bool = False


class RequestHumanHandoffInput(BaseModel):
    conversation_id: UUID
    lead_id: UUID | None = None
    reason: HandoffReason
    note: str | None = None


class GeocodeAddressInput(BaseModel):
    lead_id: UUID
    conversation_id: UUID | None = None
    address: str


class EstimateSolarPotentialInput(BaseModel):
    analysis_id: UUID
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    average_energy_bill: Decimal | None = None
