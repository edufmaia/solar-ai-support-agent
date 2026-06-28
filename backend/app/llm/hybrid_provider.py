from collections.abc import Callable

from ..config.settings import Settings, get_settings
from ..schemas.llm import LLMRequest, LLMResponse
from .base import BaseLLMProvider, LLMProviderConfigurationError
from .mock_provider import MockLLMProvider


class HybridLLMProvider(BaseLLMProvider):
    """Routes each turn between the mock (free) and a real provider (tokens).

    Balanced policy: scripted turns — greeting, collecting core fields
    (city/bill/address) and the solar pre-analysis summary — are answered by
    the mock at zero cost; the real LLM is only called once the core data is
    complete and there is a free-form turn to interpret.

    The real provider is built lazily, so greeting/collection turns work even
    if the real provider's API key is absent. Each turn's `LLMResponse` carries
    the actual provider/model/tokens/cost, so cost tracking stays accurate.
    """

    provider_name = "hybrid"
    event_source = "hybrid_llm_provider"

    def __init__(
        self,
        mock: BaseLLMProvider | None = None,
        real: BaseLLMProvider | None = None,
        real_factory: Callable[[], BaseLLMProvider] | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.mock = mock or MockLLMProvider()
        self._real = real
        self._real_factory = real_factory

    @property
    def real(self) -> BaseLLMProvider:
        if self._real is None:
            factory = self._real_factory or self._default_real_factory
            self._real = factory()
        return self._real

    def _default_real_factory(self) -> BaseLLMProvider:
        # Imported here to avoid a circular import with factory.py.
        from .claude_provider import ClaudeProvider
        from .openai_provider import OpenAIProvider

        target = self.settings.hybrid_real_provider.lower().strip()
        if target == "openai":
            return OpenAIProvider(settings=self.settings)
        if target == "claude":
            return ClaudeProvider(settings=self.settings)
        raise LLMProviderConfigurationError(
            f"Unsupported HYBRID_REAL_PROVIDER '{self.settings.hybrid_real_provider}'. "
            "Supported values: openai, claude."
        )

    def generate_response(self, request: LLMRequest) -> LLMResponse:
        if self._should_use_mock(request):
            return self.mock.generate_response(request)
        return self.real.generate_response(request)

    def _should_use_mock(self, request: LLMRequest) -> bool:
        lead_data = request.lead_data or {}
        extracted = request.extracted_data or {}

        has_city = bool(extracted.get("city") or lead_data.get("city"))
        has_bill = bool(
            extracted.get("average_energy_bill") or lead_data.get("average_energy_bill")
        )
        has_address = bool(extracted.get("address") or lead_data.get("address"))
        has_lead = request.lead_data is not None or request.lead_score is not None

        # Solar pre-analysis summary -> templated mock (no tokens).
        if request.geospatial is not None:
            return True

        # Greeting / nothing substantive yet -> mock welcome.
        if not has_lead and not (has_city or has_bill or has_address):
            return True

        # Still collecting the core fields -> scripted mock ask.
        if not (has_city and has_bill and has_address):
            return True

        # Core data complete and a free-form turn to interpret -> real LLM.
        return False
