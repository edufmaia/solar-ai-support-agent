from decimal import Decimal
from uuid import uuid4

from app.schemas.geocoding import GeocodingResult
from app.schemas.geospatial import GeospatialAnalysisCreate
from app.schemas.tools import GeocodeAddressInput
from app.tools import GeocodeAddressTool


class _FakeProvider:
    def __init__(self, result):
        self.result = result
        self.queried = None

    def geocode(self, address):
        self.queried = address
        return self.result


class _FakeGeoRepository:
    def __init__(self):
        self.created = None

    def create(self, data: GeospatialAnalysisCreate):
        self.created = data
        return "saved-analysis"


def test_geocode_tool_geocodes_and_persists():
    provider = _FakeProvider(
        GeocodingResult(
            found=True,
            formatted_address="Rua das Flores, 123, Natal",
            latitude=Decimal("-5.79"),
            longitude=Decimal("-35.21"),
            address_confidence="high",
            raw_response={"provider": "mock"},
        )
    )
    repo = _FakeGeoRepository()
    tool = GeocodeAddressTool(provider, repo)
    lead_id = uuid4()
    conversation_id = uuid4()

    out = tool.execute(
        GeocodeAddressInput(
            lead_id=lead_id, conversation_id=conversation_id, address="Rua das Flores, 123"
        )
    )

    assert out == "saved-analysis"
    assert provider.queried == "Rua das Flores, 123"
    assert repo.created.lead_id == lead_id
    assert repo.created.conversation_id == conversation_id
    assert repo.created.raw_address == "Rua das Flores, 123"
    assert repo.created.latitude == Decimal("-5.79")
    assert repo.created.address_confidence == "high"


def test_geocode_tool_persists_not_found_result():
    provider = _FakeProvider(GeocodingResult(found=False, address_confidence="unknown"))
    repo = _FakeGeoRepository()
    tool = GeocodeAddressTool(provider, repo)

    tool.execute(GeocodeAddressInput(lead_id=uuid4(), address="endereço inexistente"))

    assert repo.created.latitude is None
    assert repo.created.address_confidence == "unknown"


def test_geocode_tool_schema():
    tool = GeocodeAddressTool(_FakeProvider(GeocodingResult(found=False)), _FakeGeoRepository())

    schema = tool.tool_schema()

    assert schema["name"] == "geocode_address"
    assert "address" in schema["input_schema"]["properties"]
