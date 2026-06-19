from abc import ABC, abstractmethod
from decimal import Decimal

from ..schemas.solar import SolarPotentialResult


class SolarProviderError(Exception):
    """Base exception for solar provider errors."""


class SolarProviderConfigurationError(SolarProviderError):
    """Raised when a solar provider is misconfigured."""


class SolarProviderInvocationError(SolarProviderError):
    """Raised when a solar provider request fails."""


class BaseSolarProvider(ABC):
    provider_name: str

    @abstractmethod
    def estimate(
        self,
        latitude: Decimal | None,
        longitude: Decimal | None,
        average_energy_bill: Decimal | None,
    ) -> SolarPotentialResult:
        """Estimate preliminary solar potential for a location/lead."""
