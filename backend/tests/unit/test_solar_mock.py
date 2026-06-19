from decimal import Decimal

import pytest

from app.solar.base import BaseSolarProvider
from app.solar.mock_provider import MockSolarProvider

LAT = Decimal("-5.7945")
LON = Decimal("-35.2110")


def test_estimates_from_energy_bill_medium_confidence():
    result = MockSolarProvider().estimate(LAT, LON, Decimal("350"))

    assert result.solar_data_available is True
    assert result.confidence_level == "medium"
    assert result.estimated_system_kwp == Decimal("3.64")
    assert result.estimated_panel_min == 6
    assert result.estimated_panel_max == 8
    assert result.requires_technical_review is False


def test_large_bill_requires_technical_review():
    result = MockSolarProvider().estimate(LAT, LON, Decimal("1200"))

    assert result.estimated_system_kwp >= Decimal("10")
    assert result.requires_technical_review is True
    assert result.confidence_level == "medium"


def test_fallback_without_bill_is_deterministic_and_low_confidence():
    provider = MockSolarProvider()

    first = provider.estimate(LAT, LON, None)
    second = provider.estimate(LAT, LON, None)

    assert first.solar_data_available is True
    assert first.confidence_level == "low"
    assert first.requires_technical_review is True
    assert first.estimated_system_kwp == second.estimated_system_kwp
    assert first.estimated_panel_max == second.estimated_panel_max


def test_missing_coordinates_returns_no_data():
    result = MockSolarProvider().estimate(None, None, Decimal("350"))

    assert result.solar_data_available is False
    assert result.confidence_level == "unknown"
    assert result.estimated_system_kwp is None


def test_base_solar_provider_is_abstract():
    with pytest.raises(TypeError):
        BaseSolarProvider()
