from ..config.settings import Settings, get_settings
from .base import BaseSolarProvider, SolarProviderConfigurationError
from .mock_provider import MockSolarProvider


def build_solar_provider(settings: Settings | None = None) -> BaseSolarProvider:
    active_settings = settings or get_settings()
    provider_name = active_settings.solar_provider.lower().strip()

    if provider_name == "mock":
        return MockSolarProvider()

    raise SolarProviderConfigurationError(
        f"Unsupported SOLAR_PROVIDER '{active_settings.solar_provider}'. "
        "Supported values: mock."
    )
