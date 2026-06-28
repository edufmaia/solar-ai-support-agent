import pytest
from app.config.settings import Settings
from app.geocoding.base import GeocodingProviderConfigurationError
from app.geocoding.factory import build_geocoding_provider
from app.geocoding.mock_provider import MockGeocodingProvider
from app.geocoding.nominatim_provider import NominatimGeocodingProvider


def test_factory_builds_mock_by_default():
    assert isinstance(
        build_geocoding_provider(Settings(geocoding_provider="mock")), MockGeocodingProvider
    )


def test_factory_builds_nominatim():
    assert isinstance(
        build_geocoding_provider(Settings(geocoding_provider="nominatim")),
        NominatimGeocodingProvider,
    )


def test_factory_rejects_unknown_provider():
    with pytest.raises(GeocodingProviderConfigurationError):
        build_geocoding_provider(Settings(geocoding_provider="bogus"))
