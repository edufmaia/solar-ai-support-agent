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
        has_address = bool(lead_data.get("address"))
        has_geospatial = request.geospatial is not None
        phone = lead_data.get("phone") or extracted_data.get("phone")

        content: str
        next_state: str

        if has_geospatial:
            # The analysis already ran — report it regardless of temperature.
            # Only promise a specialist follow-up once we have a way to reach the
            # lead; otherwise collect the contact first.
            name = lead_data.get("name") or extracted_data.get("name")
            content, next_state = self._post_analysis_message(request.geospatial or {}, phone, name)
        elif request.lead_temperature == "hot":
            # A hot lead progresses through states instead of repeating one line:
            # ask for the address -> ask for consent -> (analysis handled above).
            if has_address:
                content = (
                    "Perfeito, já registrei seu endereço. Se você autorizar, sigo com uma "
                    "pré-análise geoespacial preliminar do potencial solar nesse local."
                )
                next_state = "awaiting_geospatial_consent"
            else:
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

    def _post_analysis_message(
        self, geospatial: dict, phone: str | None, name: str | None = None
    ) -> tuple[str, str]:
        """Report the completed analysis, then either confirm the specialist
        follow-up (if we have a contact) or collect the contact first. Only the
        still-missing contact fields are requested (don't re-ask a known name)."""
        estimate = self._geospatial_estimate(geospatial)
        if phone:
            content = (
                f"{estimate} Já encaminhei seu caso a um especialista, que vai te "
                f"contatar no {phone} com a proposta detalhada."
            )
            return content, "handed_off_to_specialist"
        if name:
            ask = "qual é o seu telefone (ou WhatsApp)?"
        else:
            ask = "qual é o seu nome e telefone (ou WhatsApp)?"
        content = f"{estimate} Para um especialista preparar sua proposta e te retornar, {ask}"
        return content, "awaiting_contact"

    @staticmethod
    def _geospatial_estimate(geospatial: dict) -> str:
        """Build the estimate sentence, verbalizing the panel quantity when available."""
        solar = geospatial.get("solar") or {}
        panel_min = solar.get("estimated_panel_min")
        panel_max = solar.get("estimated_panel_max")

        if solar.get("solar_data_available") and panel_min and panel_max:
            kwp = solar.get("estimated_system_kwp")
            system = f" (um sistema de aproximadamente {kwp} kWp)" if kwp else ""
            return (
                "Concluí uma pré-análise preliminar do seu endereço. Para o seu padrão de "
                f"consumo, estimo entre {panel_min} e {panel_max} placas solares{system}. "
                "É uma estimativa preliminar e não substitui vistoria técnica."
            )

        return "Concluí uma pré-análise preliminar do seu endereço e o potencial é promissor."
