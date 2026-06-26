from abc import ABC, abstractmethod

from ...schemas.lead_extraction import LeadExtractionResult


class BaseLeadFieldExtractor(ABC):
    """Provider-agnostic structured lead extraction from conversation history."""

    @abstractmethod
    def extract_fields(
        self, history: list[dict], known_lead: dict | None
    ) -> LeadExtractionResult:
        """Return consolidated lead fields. Raises LLMProviderInvocationError or
        ValueError on failure; the caller decides whether to fall back."""
