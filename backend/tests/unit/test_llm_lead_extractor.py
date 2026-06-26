from app.llm.base import LLMProviderInvocationError
from app.schemas.lead_extraction import LeadExtractionResult
from app.services.lead_extraction_service import LeadExtractionService
from app.services.lead_extractor import LeadExtractor
from app.services.llm_lead_extractor import LLMLeadExtractor, build_lead_extractor


class _OkProvider:
    def extract_fields(self, history, known_lead):
        return LeadExtractionResult(name="Eduardo Freire Maia", email="a@b.com")


class _FailProvider:
    def extract_fields(self, history, known_lead):
        raise LLMProviderInvocationError("boom")


def test_uses_provider_result_on_success():
    ext = LLMLeadExtractor(provider=_OkProvider())
    result = ext.extract("Eduardo Freire Maia",
                         history=[{"role": "assistant", "content": "Qual seu nome?"}])
    assert result.name == "Eduardo Freire Maia"
    assert ext.last_fallback_reason is None


def test_falls_back_to_regex_on_provider_failure():
    ext = LLMLeadExtractor(provider=_FailProvider(), fallback=LeadExtractionService())
    result = ext.extract("me chamo Ana", history=[])
    assert result.name == "Ana"
    assert ext.last_fallback_reason is not None


def test_is_a_lead_extractor():
    assert isinstance(LLMLeadExtractor(provider=_OkProvider()), LeadExtractor)


def test_build_lead_extractor_regex_only_when_disabled():
    from app.config.settings import Settings
    ext = build_lead_extractor(Settings(lead_extraction_provider="regex"))
    assert isinstance(ext, LLMLeadExtractor)
    # provider disabled -> always regex, no failure reason recorded
    result = ext.extract("me chamo Ana", history=[])
    assert result.name == "Ana"
    assert ext.last_fallback_reason is None
