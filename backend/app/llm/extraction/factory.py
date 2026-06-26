from ...config.settings import Settings, get_settings
from ..base import LLMProviderConfigurationError
from .base import BaseLeadFieldExtractor
from .claude_extractor import ClaudeFieldExtractor
from .openai_extractor import OpenAIFieldExtractor


def _resolve(settings: Settings) -> str:
    target = settings.lead_extraction_provider.lower().strip()
    if target != "auto":
        return target
    if settings.llm_provider.lower().strip() == "hybrid":
        return settings.hybrid_real_provider.lower().strip()
    return settings.llm_provider.lower().strip()


def build_lead_extraction_provider(settings: Settings | None = None) -> BaseLeadFieldExtractor | None:
    active = settings or get_settings()
    target = _resolve(active)

    if target in ("regex", "mock"):
        return None
    if target == "openai":
        return OpenAIFieldExtractor(settings=active)
    if target == "claude":
        return ClaudeFieldExtractor(settings=active)

    raise LLMProviderConfigurationError(
        f"Unsupported LEAD_EXTRACTION_PROVIDER '{active.lead_extraction_provider}'. "
        "Supported values: auto, openai, claude, regex."
    )
