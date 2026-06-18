from abc import ABC, abstractmethod

from ..schemas.geocoding import GeocodingResult


class GeocodingProviderError(Exception):
    """Base exception for geocoding provider errors."""


class GeocodingProviderConfigurationError(GeocodingProviderError):
    """Raised when a geocoding provider is misconfigured."""


class GeocodingProviderInvocationError(GeocodingProviderError):
    """Raised when a geocoding provider request fails."""


class BaseGeocodingProvider(ABC):
    provider_name: str

    @abstractmethod
    def geocode(self, address: str) -> GeocodingResult:
        """Convert an address string into coordinates."""
