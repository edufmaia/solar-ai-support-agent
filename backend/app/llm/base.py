from abc import ABC, abstractmethod

from ..schemas.llm import LLMRequest, LLMResponse


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""


class LLMProviderConfigurationError(LLMProviderError):
    """Raised when an LLM provider is misconfigured."""


class LLMProviderInvocationError(LLMProviderError):
    """Raised when an LLM provider request fails."""


class BaseLLMProvider(ABC):
    provider_name: str
    event_source: str

    @property
    def event_type(self) -> str:
        return f"llm_{self.provider_name}_response_generated"

    @abstractmethod
    def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response for the given conversation context."""
