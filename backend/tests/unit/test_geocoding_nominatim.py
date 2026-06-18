from decimal import Decimal

import httpx
import pytest

from app.config.settings import Settings
from app.geocoding.base import GeocodingProviderInvocationError
from app.geocoding.nominatim_provider import NominatimGeocodingProvider


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return _FakeResponse(self._payload)


class _RaisingClient:
    def get(self, *args, **kwargs):
        raise httpx.RequestError("boom")


def _settings():
    return Settings(
        nominatim_base_url="https://nominatim.example/search",
        nominatim_user_agent="test-agent",
        geocoding_timeout_seconds=5.0,
    )


def test_nominatim_high_confidence_with_house_number():
    payload = [
        {
            "lat": "-5.79",
            "lon": "-35.21",
            "display_name": "Rua das Flores, 123, Natal",
            "address": {"house_number": "123", "road": "Rua das Flores"},
        }
    ]
    provider = NominatimGeocodingProvider(settings=_settings(), client=_FakeClient(payload))

    result = provider.geocode("Rua das Flores, 123")

    assert result.found is True
    assert result.address_confidence == "high"
    assert result.latitude == Decimal("-5.79")
    assert result.longitude == Decimal("-35.21")
    assert result.formatted_address == "Rua das Flores, 123, Natal"


def test_nominatim_medium_confidence_with_road_only():
    payload = [
        {"lat": "-5.79", "lon": "-35.21", "display_name": "Rua das Flores", "address": {"road": "Rua das Flores"}}
    ]
    provider = NominatimGeocodingProvider(settings=_settings(), client=_FakeClient(payload))

    assert provider.geocode("Rua das Flores").address_confidence == "medium"


def test_nominatim_not_found_for_empty_results():
    provider = NominatimGeocodingProvider(settings=_settings(), client=_FakeClient([]))

    result = provider.geocode("endereço inexistente")

    assert result.found is False
    assert result.address_confidence == "unknown"


def test_nominatim_sends_user_agent_header():
    client = _FakeClient([{"lat": "0", "lon": "0", "display_name": "x", "address": {}}])
    provider = NominatimGeocodingProvider(settings=_settings(), client=client)

    provider.geocode("Rua X")

    assert client.calls[0]["headers"]["User-Agent"] == "test-agent"


def test_nominatim_wraps_client_error():
    provider = NominatimGeocodingProvider(settings=_settings(), client=_RaisingClient())

    with pytest.raises(GeocodingProviderInvocationError):
        provider.geocode("Rua X")


class _MalformedJsonClient:
    def get(self, *args, **kwargs):
        class _Resp:
            def raise_for_status(self):
                return None

            def json(self):
                raise ValueError("malformed body")

        return _Resp()


def test_nominatim_wraps_malformed_json_body():
    provider = NominatimGeocodingProvider(settings=_settings(), client=_MalformedJsonClient())

    with pytest.raises(GeocodingProviderInvocationError):
        provider.geocode("Rua X")
