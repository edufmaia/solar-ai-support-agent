import json
from typing import Any

from anthropic import Anthropic, APIError

from ...config.settings import Settings, get_settings
from ...schemas.lead_extraction import LeadExtractionResult
from ..base import LLMProviderConfigurationError, LLMProviderInvocationError
from .base import BaseLeadFieldExtractor
from .prompt import (
    LEAD_FIELDS_TOOL,
    build_extraction_system_prompt,
    render_known_lead,
    result_from_fields,
)

_DEFAULT_MODEL = "claude-haiku-4-5"


class ClaudeFieldExtractor(BaseLeadFieldExtractor):
    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.model_name = self.settings.lead_extraction_model or _DEFAULT_MODEL
        self.max_tokens = self.settings.lead_extraction_max_tokens
        if not self.settings.anthropic_api_key:
            raise LLMProviderConfigurationError(
                "ANTHROPIC_API_KEY is required for Claude lead extraction."
            )
        self.client = client or Anthropic(api_key=self.settings.anthropic_api_key)

    def extract_fields(self, history: list[dict], known_lead: dict | None) -> LeadExtractionResult:
        user_content = (
            "Dados já conhecidos do lead (JSON):\n"
            f"{render_known_lead(known_lead)}\n\n"
            "Histórico da conversa (JSON):\n"
            f"{json.dumps(history, ensure_ascii=False, default=str)}"
        )
        try:
            # tools/tool_choice/messages are dict literals the SDK accepts at
            # runtime; they don't match the typed overloads statically.
            message = self.client.messages.create(  # type: ignore[call-overload]
                model=self.model_name,
                max_tokens=self.max_tokens,
                system=build_extraction_system_prompt(),
                tools=[LEAD_FIELDS_TOOL],
                tool_choice={"type": "tool", "name": "record_lead_fields"},
                messages=[{"role": "user", "content": user_content}],
            )
        except APIError as exc:
            raise LLMProviderInvocationError(f"Anthropic extraction request failed: {exc}") from exc

        for block in getattr(message, "content", None) or []:
            if getattr(block, "type", None) == "tool_use":
                try:
                    return result_from_fields(block.input)
                except ValueError as exc:
                    raise LLMProviderInvocationError(str(exc)) from exc
        raise LLMProviderInvocationError("Anthropic extraction returned no tool_use block.")
