from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

GeoConfidence = Literal["low", "medium", "high", "unknown"]


class GeocodingResult(BaseModel):
    found: bool
    formatted_address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    address_confidence: GeoConfidence | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)
