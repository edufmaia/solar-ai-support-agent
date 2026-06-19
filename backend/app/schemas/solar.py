from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

SolarConfidence = Literal["low", "medium", "high", "unknown"]


class SolarPotentialResult(BaseModel):
    solar_data_available: bool
    estimated_panel_min: int | None = None
    estimated_panel_max: int | None = None
    estimated_system_kwp: Decimal | None = None
    confidence_level: SolarConfidence | None = None
    requires_technical_review: bool = False
    raw_response: dict[str, Any] = Field(default_factory=dict)
