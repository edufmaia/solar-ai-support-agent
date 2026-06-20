import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from anthropic import Anthropic, APIError

from ..config.settings import Settings, get_settings
from ..schemas.llm import LLMRequest, LLMResponse
from .base import BaseLLMProvider, LLMProviderConfigurationError, LLMProviderInvocationError
from .context import geospatial_prompt_section


class ClaudeProvider(BaseLLMProvider):
    provider_name = "claude"
    event_source = "claude_provider"

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.model_name = self.settings.claude_model
        self.max_tokens = self.settings.claude_max_tokens

        if not self.settings.anthropic_api_key:
            raise LLMProviderConfigurationError(
                "ANTHROPIC_API_KEY is required when LLM_PROVIDER=claude."
            )

        self.client = client or Anthropic(api_key=self.settings.anthropic_api_key)

    def generate_response(self, request: LLMRequest) -> LLMResponse:
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                system=self._build_instructions(),
                messages=[
                    {"role": "user", "content": self._build_context_prompt(request)}
                ],
            )
        except APIError as exc:
            raise LLMProviderInvocationError(
                f"Anthropic Messages API request failed: {exc}"
            ) from exc

        content = self._extract_output_text(response)
        input_tokens, output_tokens = self._extract_usage(response)
        estimated_cost = self._calculate_estimated_cost(input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model_name=getattr(response, "model", None) or self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            raw_response={
                "id": getattr(response, "id", None),
                "stop_reason": getattr(response, "stop_reason", None),
                "model": getattr(response, "model", None) or self.model_name,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            },
            next_state=None,
        )

    def _build_instructions(self) -> str:
        return (
            "Você é um assistente comercial inicial para empresas de energia solar. "
            "Responda sempre em português do Brasil, com tom profissional, claro, consultivo e objetivo. "
            "Colete dados faltantes do lead quando necessário. "
            "Não prometa economia exata. "
            "Não prometa quantidade exata de placas, mas quando houver uma pré-análise "
            "geoespacial/solar no contexto, você pode citar a faixa estimada de placas e a "
            "potência (kWp), sempre deixando claro que é uma estimativa preliminar. "
            "Deixe claro que qualquer análise é preliminar e não substitui vistoria técnica. "
            "Quando necessário, sugira encaminhamento para análise humana ou técnica."
        )

    def _build_context_prompt(self, request: LLMRequest) -> str:
        lead_data = json.dumps(request.lead_data or {}, ensure_ascii=False, default=str)
        extracted_data = json.dumps(request.extracted_data or {}, ensure_ascii=False, default=str)
        geospatial = geospatial_prompt_section(request.geospatial)

        return (
            "Contexto atual da conversa:\n"
            f"- Estado atual: {request.current_state or 'não informado'}\n"
            f"- Lead score: {request.lead_score if request.lead_score is not None else 'não informado'}\n"
            f"- Lead temperature: {request.lead_temperature or 'não informado'}\n"
            f"- Dados consolidados do lead: {lead_data}\n"
            f"- Dados extraídos da mensagem atual: {extracted_data}\n"
            f"{geospatial}\n"
            "Mensagem do usuário:\n"
            f"{request.user_message}\n\n"
            "Responda ao usuário considerando esse contexto."
        )

    def _extract_output_text(self, response: Any) -> str:
        blocks = getattr(response, "content", None) or []
        collected_text: list[str] = []

        for block in blocks:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", None)
                if text:
                    collected_text.append(text)

        content = "\n".join(part.strip() for part in collected_text if part).strip()
        if not content:
            raise LLMProviderInvocationError("Anthropic response did not contain text output.")

        return content

    def _extract_usage(self, response: Any) -> tuple[int, int]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return 0, 0

        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        return int(input_tokens), int(output_tokens)

    def _calculate_estimated_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        input_cost = (
            Decimal(input_tokens) / Decimal("1000000")
        ) * self.settings.claude_input_price_per_1m_tokens
        output_cost = (
            Decimal(output_tokens) / Decimal("1000000")
        ) * self.settings.claude_output_price_per_1m_tokens

        return (input_cost + output_cost).quantize(
            Decimal("0.000001"),
            rounding=ROUND_HALF_UP,
        )
