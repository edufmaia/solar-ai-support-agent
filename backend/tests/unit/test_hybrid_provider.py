from decimal import Decimal
from uuid import uuid4

from app.llm.hybrid_provider import HybridLLMProvider
from app.schemas.llm import LLMRequest, LLMResponse


class _Stub:
    def __init__(self, label):
        self.label = label
        self.calls = 0

    def generate_response(self, request):
        self.calls += 1
        return LLMResponse(content=self.label, provider=self.label, model_name=self.label)


def _hybrid():
    mock = _Stub("mock")
    real = _Stub("real")
    return HybridLLMProvider(mock=mock, real=real), mock, real


def _request(**overrides) -> LLMRequest:
    base = dict(conversation_id=uuid4(), user_message="oi")
    base.update(overrides)
    return LLMRequest(**base)


def test_greeting_uses_mock():
    hybrid, mock, real = _hybrid()
    out = hybrid.generate_response(_request())
    assert out.provider == "mock"
    assert mock.calls == 1 and real.calls == 0


def test_collecting_core_fields_uses_mock():
    hybrid, mock, real = _hybrid()
    # has bill but missing city/address -> still collecting
    hybrid.generate_response(_request(lead_data={"average_energy_bill": "800"}, lead_score=40))
    assert mock.calls == 1 and real.calls == 0


def test_solar_summary_uses_mock():
    hybrid, mock, real = _hybrid()
    hybrid.generate_response(
        _request(
            lead_data={"city": "Natal", "average_energy_bill": "800", "address": "Rua X"},
            geospatial={"solar": {"solar_data_available": True}},
        )
    )
    assert mock.calls == 1 and real.calls == 0


def test_core_complete_freeform_uses_real():
    hybrid, mock, real = _hybrid()
    out = hybrid.generate_response(
        _request(
            user_message="quanto tempo leva a instalação?",
            lead_data={"city": "Natal", "average_energy_bill": "800", "address": "Rua X, 1"},
            lead_score=72,
        )
    )
    assert out.provider == "real"
    assert real.calls == 1 and mock.calls == 0


def test_real_provider_is_lazy():
    built = {"n": 0}

    def factory():
        built["n"] += 1
        return _Stub("real")

    hybrid = HybridLLMProvider(mock=_Stub("mock"), real_factory=factory)
    # only mock turns so far -> real never constructed
    hybrid.generate_response(_request())
    assert built["n"] == 0
    # a real turn triggers construction once
    hybrid.generate_response(
        _request(lead_data={"city": "Natal", "average_energy_bill": "800", "address": "R"}, lead_score=72)
    )
    assert built["n"] == 1
