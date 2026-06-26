import pytest

from app.config.settings import Settings
from app.solar.base import SolarProviderConfigurationError
from app.solar.factory import build_solar_provider
from app.solar.footprint_provider import FootprintSolarProvider
from app.solar.mock_provider import MockSolarProvider


def test_factory_builds_mock_by_default():
    assert isinstance(build_solar_provider(Settings(solar_provider="mock")), MockSolarProvider)


def test_factory_builds_footprint():
    provider = build_solar_provider(Settings(solar_provider="footprint"))
    assert isinstance(provider, FootprintSolarProvider)


def test_factory_rejects_unknown_provider():
    with pytest.raises(SolarProviderConfigurationError):
        build_solar_provider(Settings(solar_provider="bogus"))
