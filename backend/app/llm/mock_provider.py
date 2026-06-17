from decimal import Decimal

from ..schemas.llm import LLMRequest, LLMResponse
from .base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    PROVIDER_NAME = "mock"
    MODEL_NAME = "mock-agent-v1"
    provider_name = PROVIDER_NAME
    event_source = "mock_llm_provider"

    def generate_response(self, request: LLMRequest) -> LLMResponse:
        lead_data = request.lead_data or {}
        extracted_data = request.extracted_data or {}

        has_city = extracted_data.get("city") is not None or lead_data.get("city") is not None
        has_bill = (
            extracted_data.get("average_energy_bill") is not None
            or lead_data.get("average_energy_bill") is not None
        )

        content: str
        next_state: str

        if request.lead_temperature == "hot":
            content = (
                "Seu perfil já mostra um bom potencial preliminar para energia solar. "
                "Se quiser, você pode me informar o endereço do imóvel para avançarmos "
                "para uma pré-análise geoespacial preliminar."
            )
            next_state = "ready_for_geospatial_pre_analysis"
        elif request.lead_temperature == "warm":
            if not has_city and not has_bill:
                content = (
                    "Seu perfil já tem sinais iniciais interessantes, mas ainda faltam alguns "
                    "dados para uma pré-análise preliminar. Me informe sua cidade e o valor "
                    "médio da sua conta de energia."
                )
                next_state = "awaiting_city_and_bill"
            elif has_city and not has_bill:
                content = (
                    "Seu perfil já tem um bom sinal inicial. Para continuar a análise preliminar, "
                    "qual é o valor médio da sua conta de energia?"
                )
                next_state = "awaiting_energy_bill"
            elif has_bill and not has_city:
                content = (
                    "Já tenho uma estimativa da conta de energia. Para seguir com a análise preliminar, "
                    "você pode me informar sua cidade ou endereço?"
                )
                next_state = "awaiting_location"
            else:
                content = (
                    "Seu perfil já tem um potencial inicial interessante. Para refinar a análise preliminar, "
                    "você pode me informar o endereço do imóvel ou mais detalhes do cenário?"
                )
                next_state = "collecting_additional_details"
        elif request.lead_temperature == "cold":
            content = (
                "Consigo te orientar de forma preliminar, mas ainda preciso entender melhor o seu cenário. "
                "Se puder, me informe sua cidade, o valor médio da sua conta e o tipo do imóvel."
            )
            next_state = "collecting_basic_context"
        elif not has_city and not has_bill:
            content = (
                "Posso seguir com uma pré-análise preliminar de energia solar. "
                "Para começar, me informe sua cidade e o valor médio da sua conta de energia."
            )
            next_state = "awaiting_city_and_bill"
        elif has_city and not has_bill:
            content = (
                "Perfeito, já identifiquei sua cidade. Para seguir com uma pré-análise preliminar, "
                "qual é o valor médio da sua conta de energia?"
            )
            next_state = "awaiting_energy_bill"
        elif has_bill and not has_city:
            content = (
                "Perfeito, já identifiquei o valor médio da sua conta. Para seguir com uma pré-análise preliminar, "
                "você pode me informar sua cidade ou endereço?"
            )
            next_state = "awaiting_location"
        else:
            content = (
                "Ótimo, já tenho sua cidade e uma estimativa da conta de energia. "
                "Com isso já é possível iniciar uma pré-análise preliminar. Se quiser, "
                "você pode me informar o endereço do imóvel para continuarmos."
            )
            next_state = "ready_for_pre_analysis"

        return LLMResponse(
            content=content,
            provider=self.PROVIDER_NAME,
            model_name=self.MODEL_NAME,
            input_tokens=0,
            output_tokens=0,
            estimated_cost=Decimal("0"),
            raw_response={
                "provider": self.PROVIDER_NAME,
                "model_name": self.MODEL_NAME,
                "next_state": next_state,
            },
            next_state=next_state,
        )
