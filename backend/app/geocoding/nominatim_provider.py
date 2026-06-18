from decimal import Decimal
from typing import Any

import httpx

from ..config.settings import Settings, get_settings
from ..schemas.geocoding import GeocodingResult
from .base import BaseGeocodingProvider, GeocodingProviderInvocationError


class NominatimGeocodingProvider(BaseGeocodingProvider):
    provider_name = "nominatim"

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client

    def geocode(self, address: str) -> GeocodingResult:
        if not address or not address.strip():
            return GeocodingResult(
                found=False,
                address_confidence="unknown",
                raw_response={"provider": "nominatim", "query": address},
            )

        params = {"q": address, "format": "json", "limit": 1, "addressdetails": 1}
        headers = {"User-Agent": self.settings.nominatim_user_agent}

        try:
            if self.client is not None:
                response = self.client.get(
                    self.settings.nominatim_base_url, params=params, headers=headers
                )
            else:
                response = httpx.get(
                    self.settings.nominatim_base_url,
                    params=params,
                    headers=headers,
                    timeout=self.settings.geocoding_timeout_seconds,
                )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise GeocodingProviderInvocationError(
                f"Nominatim request failed: {exc}"
            ) from exc

        if not data:
            return GeocodingResult(
                found=False,
                address_confidence="unknown",
                raw_response={"provider": "nominatim", "query": address, "results": []},
            )

        top = data[0]
        address_details = top.get("address", {}) or {}
        if address_details.get("house_number"):
            confidence = "high"
        elif address_details.get("road"):
            confidence = "medium"
        else:
            confidence = "low"

        return GeocodingResult(
            found=True,
            formatted_address=top.get("display_name"),
            latitude=Decimal(str(top["lat"])),
            longitude=Decimal(str(top["lon"])),
            address_confidence=confidence,
            raw_response={"provider": "nominatim", "result": top},
        )
