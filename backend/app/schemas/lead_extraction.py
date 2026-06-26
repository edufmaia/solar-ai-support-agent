from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel


PropertyType = Literal["residential", "commercial"]
LeadIntent = Literal["solar_quote", "solar_interest", "general_question"]


class LeadExtractionResult(BaseModel):
    name: str | None = None
    email: str | None = None
    city: str | None = None
    average_energy_bill: Decimal | None = None
    property_type: PropertyType | None = None
    intent: LeadIntent = "general_question"
    has_solar_interest: bool = False
    wants_human: bool = False
    phone: str | None = None
    address: str | None = None
    geo_consent: bool = False

    def has_relevant_data(self) -> bool:
        return any(
            [
                self.has_solar_interest,
                self.name is not None,
                self.email is not None,
                self.city is not None,
                self.average_energy_bill is not None,
                self.property_type is not None,
                self.phone is not None,
                self.address is not None,
            ]
        )

    def to_event_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "intent": self.intent,
            "has_solar_interest": self.has_solar_interest,
            "wants_human": self.wants_human,
            "geo_consent": self.geo_consent,
        }

        if self.name is not None:
            payload["name"] = self.name
        if self.email is not None:
            payload["email"] = self.email
        if self.city is not None:
            payload["city"] = self.city
        if self.average_energy_bill is not None:
            payload["average_energy_bill"] = (
                int(self.average_energy_bill)
                if self.average_energy_bill == self.average_energy_bill.to_integral_value()
                else float(self.average_energy_bill)
            )
        if self.property_type is not None:
            payload["property_type"] = self.property_type
        if self.phone is not None:
            payload["phone"] = self.phone
        if self.address is not None:
            payload["address"] = self.address

        return payload
