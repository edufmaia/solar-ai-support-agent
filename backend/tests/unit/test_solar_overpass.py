from decimal import Decimal

import httpx
import pytest

from app.config.settings import Settings
from app.solar.overpass_client import OverpassClient, OverpassError


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload=None, error=None):
        self._payload = payload
        self._error = error
        self.last_params = None

    def get(self, url, params=None, headers=None, timeout=None):
        self.last_params = params
        if self._error is not None:
            raise self._error
        return _FakeResp(self._payload)


def _client(payload=None, error=None):
    return OverpassClient(settings=Settings(), client=_FakeClient(payload=payload, error=error))


def test_parses_way_geometry_into_polygons():
    payload = {
        "elements": [
            {
                "type": "way",
                "geometry": [
                    {"lat": -5.79, "lon": -35.21},
                    {"lat": -5.7901, "lon": -35.21},
                    {"lat": -5.7901, "lon": -35.2101},
                ],
            }
        ]
    }
    polys = _client(payload=payload).buildings_around(Decimal("-5.79"), Decimal("-35.21"))
    assert len(polys) == 1
    assert polys[0][0] == (-5.79, -35.21)
    assert len(polys[0]) == 3


def test_ignores_non_way_and_empty_geometry():
    payload = {"elements": [{"type": "node", "lat": 1, "lon": 2}, {"type": "way", "geometry": []}]}
    assert _client(payload=payload).buildings_around(Decimal("-5.79"), Decimal("-35.21")) == []


def test_http_error_raises_overpass_error():
    with pytest.raises(OverpassError):
        _client(error=httpx.HTTPError("boom")).buildings_around(Decimal("-5.79"), Decimal("-35.21"))


def test_bad_json_raises_overpass_error():
    with pytest.raises(OverpassError):
        _client(error=ValueError("bad json")).buildings_around(Decimal("-5.79"), Decimal("-35.21"))
