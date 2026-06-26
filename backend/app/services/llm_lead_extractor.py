from ..config.settings import Settings
from ..llm.base import LLMProviderConfigurationError, LLMProviderError
from ..llm.extraction import BaseLeadFieldExtractor, build_lead_extraction_provider
from ..schemas.lead_extraction import LeadExtractionResult
from .lead_extraction_service import LeadExtractionService
from .lead_extractor import LeadExtractor


class LLMLeadExtractor(LeadExtractor):
    """LLM-first lead extractor with a deterministic regex fallback.

    ``provider`` may be None (LLM extraction disabled) — then every call uses
    the regex fallback and ``last_fallback_reason`` stays None (not an error)."""

    def __init__(
        self,
        provider: BaseLeadFieldExtractor | None,
        fallback: LeadExtractor | None = None,
    ) -> None:
        self.provider = provider
        self.fallback = fallback or LeadExtractionService()
        self.last_fallback_reason: str | None = None

    def extract(
        self,
        message: str,
        *,
        history: list[dict] | None = None,
        known_lead: dict | None = None,
    ) -> LeadExtractionResult:
        self.last_fallback_reason = None
        if self.provider is None:
            return self.fallback.extract(message, history=history, known_lead=known_lead)
        try:
            return self.provider.extract_fields(history or [], known_lead)
        except (LLMProviderError, ValueError) as exc:
            self.last_fallback_reason = str(exc)
            return self.fallback.extract(message, history=history, known_lead=known_lead)


def build_lead_extractor(settings: Settings | None = None) -> LeadExtractor:
    try:
        provider = build_lead_extraction_provider(settings)
    except LLMProviderConfigurationError:
        provider = None
    return LLMLeadExtractor(provider=provider, fallback=LeadExtractionService())
