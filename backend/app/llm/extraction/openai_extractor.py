import json
from typing import Any

from openai import OpenAI, OpenAIError

from ...config.settings import Settings, get_settings
from ...schemas.lead_extraction import LeadExtractionResult
from ..base import LLMProviderConfigurationError, LLMProviderInvocationError
from .base import BaseLeadFieldExtractor
from .prompt import (
    LEAD_FIELDS_JSON_SCHEMA,
    build_extraction_system_prompt,
    render_known_lead,
    result_from_fields,
)

_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIFieldExtractor(BaseLeadFieldExtractor):
    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.model_name = self.settings.lead_extraction_model or _DEFAULT_MODEL
        if not self.settings.openai_api_key:
            raise LLMProviderConfigurationError(
                "OPENAI_API_KEY is required for OpenAI lead extraction."
            )
        self.client = client or OpenAI(api_key=self.settings.openai_api_key)

    def extract_fields(self, history: list[dict], known_lead: dict | None) -> LeadExtractionResult:
        user_input = (
            "Dados já conhecidos do lead (JSON):\n"
            f"{render_known_lead(known_lead)}\n\n"
            "Histórico da conversa (JSON):\n"
            f"{json.dumps(history, ensure_ascii=False, default=str)}"
        )
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=build_extraction_system_prompt(),
                input=user_input,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "lead_fields",
                        "schema": LEAD_FIELDS_JSON_SCHEMA,
                        "strict": False,
                    }
                },
            )
        except OpenAIError as exc:
            raise LLMProviderInvocationError(
                f"OpenAI extraction request failed: {exc}"
            ) from exc

        raw = getattr(response, "output_text", None)
        if not raw:
            raise LLMProviderInvocationError("OpenAI extraction returned no output_text.")
        try:
            fields = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMProviderInvocationError(f"OpenAI extraction returned invalid JSON: {exc}") from exc
        try:
            return result_from_fields(fields)
        except ValueError as exc:
            raise LLMProviderInvocationError(str(exc)) from exc
