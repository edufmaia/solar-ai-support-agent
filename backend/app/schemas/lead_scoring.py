from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

LeadIntent = Literal["solar_quote", "solar_interest", "general_question"]
PropertyType = Literal["residential", "commercial"]
LeadTemperature = Literal["cold", "warm", "hot"]


class LeadScoringInput(BaseModel):
    name: str | None = None
    city: str | None = None
    average_energy_bill: Decimal | None = None
    property_type: PropertyType | None = None
    intent: LeadIntent | None = None
    has_solar_interest: bool = False


class LeadScoringResult(BaseModel):
    lead_score: int
    lead_temperature: LeadTemperature
    score_reasons: list[str]
