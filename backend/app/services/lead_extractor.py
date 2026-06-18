from abc import ABC, abstractmethod

from ..schemas.lead_extraction import LeadExtractionResult


class LeadExtractor(ABC):
    """Contract for extracting structured lead data from a user message.

    Implementations may be deterministic (regex) or LLM-based; the orchestrator
    depends only on this interface.
    """

    @abstractmethod
    def extract(self, message: str) -> LeadExtractionResult:
        """Extract structured lead fields from the message."""
