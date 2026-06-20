from ..config.settings import Settings, get_settings
from .base import BaseLLMProvider, LLMProviderConfigurationError
from .claude_provider import ClaudeProvider
from .hybrid_provider import HybridLLMProvider
from .mock_provider import MockLLMProvider
from .openai_provider import OpenAIProvider


def build_llm_provider(settings: Settings | None = None) -> BaseLLMProvider:
    active_settings = settings or get_settings()
    provider_name = active_settings.llm_provider.lower().strip()

    if provider_name == "mock":
        return MockLLMProvider()

    if provider_name == "openai":
        return OpenAIProvider(settings=active_settings)

    if provider_name == "claude":
        return ClaudeProvider(settings=active_settings)

    if provider_name == "hybrid":
        return HybridLLMProvider(settings=active_settings)

    raise LLMProviderConfigurationError(
        f"Unsupported LLM_PROVIDER '{active_settings.llm_provider}'. "
        "Supported values: mock, openai, claude, hybrid."
    )
