from decimal import Decimal

import pytest

from app.geocoding.base import BaseGeocodingProvider
from app.geocoding.mock_provider import MockGeocodingProvider


def test_mock_geocodes_valid_address():
    result = MockGeocodingProvider().geocode("Rua das Flores, 123, Natal")

    assert result.found is True
    assert result.formatted_address == "Rua das Flores, 123, Natal"
    assert result.latitude == Decimal("-5.7945")
    assert result.longitude == Decimal("-35.2110")
    assert result.address_confidence == "medium"


def test_mock_returns_not_found_for_empty_address():
    result = MockGeocodingProvider().geocode("   ")

    assert result.found is False
    assert result.latitude is None
    assert result.address_confidence == "unknown"


def test_base_geocoding_provider_is_abstract():
    with pytest.raises(TypeError):
        BaseGeocodingProvider()
