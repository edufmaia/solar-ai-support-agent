from decimal import Decimal

from ..schemas.geocoding import GeocodingResult
from .base import BaseGeocodingProvider


class MockGeocodingProvider(BaseGeocodingProvider):
    provider_name = "mock"

    def geocode(self, address: str) -> GeocodingResult:
        if not address or not address.strip():
            return GeocodingResult(
                found=False,
                address_confidence="unknown",
                raw_response={"provider": "mock", "query": address},
            )

        return GeocodingResult(
            found=True,
            formatted_address=address.strip(),
            latitude=Decimal("-5.7945"),
            longitude=Decimal("-35.2110"),
            address_confidence="medium",
            raw_response={"provider": "mock", "query": address},
        )
