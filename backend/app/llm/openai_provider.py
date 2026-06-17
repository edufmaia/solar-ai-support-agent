import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from openai import OpenAI, OpenAIError

from ..config.settings import Settings, get_settings
from ..schemas.llm import LLMRequest, LLMResponse
from .base import BaseLLMProvider, LLMProviderConfigurationError, LLMProviderInvocationError


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"
    event_source = "openai_provider"

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.model_name = self.settings.openai_model

        if not self.settings.openai_api_key:
            raise LLMProviderConfigurationError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai."
            )

        self.client = client or OpenAI(api_key=self.settings.openai_api_key)

    def generate_response(self, request: LLMRequest) -> LLMResponse:
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=self._build_instructions(),
                input=self._build_context_prompt(request),
            )
        except OpenAIError as exc:
            raise LLMProviderInvocationError(
                f"OpenAI Responses API request failed: {exc}"
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
                "status": getattr(response, "status", None),
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
            "Não prometa quantidade exata de placas. "
            "Deixe claro que qualquer análise é preliminar e não substitui vistoria técnica. "
            "Quando necessário, sugira encaminhamento para análise humana ou técnica."
        )

    def _build_context_prompt(self, request: LLMRequest) -> str:
        lead_data = json.dumps(request.lead_data or {}, ensure_ascii=False, default=str)
        extracted_data = json.dumps(request.extracted_data or {}, ensure_ascii=False, default=str)

        return (
            "Contexto atual da conversa:\n"
            f"- Estado atual: {request.current_state or 'não informado'}\n"
            f"- Lead score: {request.lead_score if request.lead_score is not None else 'não informado'}\n"
            f"- Lead temperature: {request.lead_temperature or 'não informado'}\n"
            f"- Dados consolidados do lead: {lead_data}\n"
            f"- Dados extraídos da mensagem atual: {extracted_data}\n\n"
            "Mensagem do usuário:\n"
            f"{request.user_message}\n\n"
            "Responda ao usuário considerando esse contexto."
        )

    def _extract_output_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text.strip()

        output_items = getattr(response, "output", None) or []
        collected_text: list[str] = []

        for item in output_items:
            if getattr(item, "type", None) != "message":
                continue

            for content_item in getattr(item, "content", None) or []:
                if getattr(content_item, "type", None) == "output_text":
                    text = getattr(content_item, "text", None)
                    if text:
                        collected_text.append(text)

        content = "\n".join(part.strip() for part in collected_text if part).strip()
        if not content:
            raise LLMProviderInvocationError("OpenAI response did not contain text output.")

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
        ) * self.settings.openai_input_price_per_1m_tokens
        output_cost = (
            Decimal(output_tokens) / Decimal("1000000")
        ) * self.settings.openai_output_price_per_1m_tokens

        return (input_cost + output_cost).quantize(
            Decimal("0.000001"),
            rounding=ROUND_HALF_UP,
        )
