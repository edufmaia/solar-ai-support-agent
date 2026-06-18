from ..config.settings import Settings, get_settings
from .base import BaseGeocodingProvider, GeocodingProviderConfigurationError
from .mock_provider import MockGeocodingProvider
from .nominatim_provider import NominatimGeocodingProvider


def build_geocoding_provider(settings: Settings | None = None) -> BaseGeocodingProvider:
    active_settings = settings or get_settings()
    provider_name = active_settings.geocoding_provider.lower().strip()

    if provider_name == "mock":
        return MockGeocodingProvider()

    if provider_name == "nominatim":
        return NominatimGeocodingProvider(settings=active_settings)

    raise GeocodingProviderConfigurationError(
        f"Unsupported GEOCODING_PROVIDER '{active_settings.geocoding_provider}'. "
        "Supported values: mock, nominatim."
    )
