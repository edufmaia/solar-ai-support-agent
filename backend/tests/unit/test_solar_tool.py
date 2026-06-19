from decimal import Decimal
from uuid import uuid4

from app.schemas.solar import SolarPotentialResult
from app.schemas.tools import EstimateSolarPotentialInput
from app.tools import EstimateSolarPotentialTool


class _FakeProvider:
    def __init__(self, result):
        self.result = result
        self.called_with = None

    def estimate(self, latitude, longitude, average_energy_bill):
        self.called_with = (latitude, longitude, average_energy_bill)
        return self.result


class _FakeGeoRepository:
    def __init__(self):
        self.updated = None

    def update_solar_data(self, analysis_id, result):
        self.updated = (analysis_id, result)
        return "saved-analysis"


def _result():
    return SolarPotentialResult(
        solar_data_available=True,
        estimated_panel_min=6,
        estimated_panel_max=8,
        estimated_system_kwp=Decimal("3.64"),
        confidence_level="medium",
        requires_technical_review=False,
        raw_response={"provider": "mock"},
    )


def test_solar_tool_estimates_and_persists():
    provider = _FakeProvider(_result())
    repo = _FakeGeoRepository()
    tool = EstimateSolarPotentialTool(provider, repo)
    analysis_id = uuid4()

    out = tool.execute(
        EstimateSolarPotentialInput(
            analysis_id=analysis_id,
            latitude=Decimal("-5.79"),
            longitude=Decimal("-35.21"),
            average_energy_bill=Decimal("350"),
        )
    )

    assert out == "saved-analysis"
    assert provider.called_with == (Decimal("-5.79"), Decimal("-35.21"), Decimal("350"))
    assert repo.updated[0] == analysis_id
    assert repo.updated[1].estimated_system_kwp == Decimal("3.64")


def test_solar_tool_handles_none_bill():
    provider = _FakeProvider(_result())
    repo = _FakeGeoRepository()
    tool = EstimateSolarPotentialTool(provider, repo)

    tool.execute(
        EstimateSolarPotentialInput(
            analysis_id=uuid4(),
            latitude=Decimal("-5.79"),
            longitude=Decimal("-35.21"),
            average_energy_bill=None,
        )
    )

    assert provider.called_with[2] is None


def test_solar_tool_schema():
    tool = EstimateSolarPotentialTool(_FakeProvider(_result()), _FakeGeoRepository())

    schema = tool.tool_schema()

    assert schema["name"] == "estimate_solar_potential"
    assert "analysis_id" in schema["input_schema"]["properties"]
