"""Standalone DB-backed check: LLM extraction history + email reach the lead.

Drives MockAgentOrchestrator.handle_chat against a real database with a
capturing LLM provider and a stub extractor. Cleans up the lead/conversation
it creates. Run inside the backend container:

    docker compose -p solar-ai-support-agent exec backend python tests/orchestrator_extraction_test.py
"""

import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.orchestrator import MockAgentOrchestrator
from app.config.database import SessionLocal
from app.schemas.chat import ChatRequest
from app.schemas.lead_extraction import LeadExtractionResult
from app.schemas.llm import LLMRequest, LLMResponse


class _CapturingLLM:
    provider_name = "mock"
    event_source = "mock_llm_provider"
    event_type = "llm_mock_response_generated"

    def __init__(self):
        self.last_request = None

    def generate_response(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(content="ok", provider="mock", model_name="mock-agent-v1")


class _StubExtractor:
    last_fallback_reason = None

    def extract(self, message, *, history=None, known_lead=None):
        return LeadExtractionResult(
            name="Eduardo Freire Maia",
            email="contato.eduardofmaia@gmail.com",
            city="Mossoró",
            address="Rua Belém, 201",
            average_energy_bill=800,
            has_solar_interest=True,
            intent="solar_interest",
        )


def main() -> None:
    session = SessionLocal()
    conversation_id: UUID | None = None
    lead_id = None
    try:
        llm = _CapturingLLM()
        orch = MockAgentOrchestrator(session, llm_provider=llm, lead_extractor=_StubExtractor())

        first = orch.handle_chat(ChatRequest(message="Olá, quero energia solar, pago 800 reais"))
        conversation_id = first.conversation_id
        orch.handle_chat(
            ChatRequest(message="Eduardo Freire Maia", conversation_id=conversation_id)
        )

        req = llm.last_request
        assert req.history is not None, "history must be passed to the provider"
        assert len(req.history) >= 2, f"expected >=2 history messages, got {req.history}"
        assert (
            req.lead_data is not None
            and req.lead_data.get("email") == "contato.eduardofmaia@gmail.com"
        ), f"email must be persisted on the lead, got {req.lead_data}"
        lead_id = req.lead_data.get("id")
        print("OK: history passed and email persisted")
    finally:
        if conversation_id is not None:
            session.execute(
                text("DELETE FROM agent_events WHERE conversation_id = :cid"),
                {"cid": str(conversation_id)},
            )
            session.execute(
                text("DELETE FROM messages WHERE conversation_id = :cid"),
                {"cid": str(conversation_id)},
            )
            session.execute(
                text("DELETE FROM conversations WHERE id = :cid"), {"cid": str(conversation_id)}
            )
        if lead_id is not None:
            session.execute(
                text("DELETE FROM geospatial_analysis WHERE lead_id = :lid"), {"lid": str(lead_id)}
            )
            session.execute(text("DELETE FROM leads WHERE id = :lid"), {"lid": str(lead_id)})
        session.commit()
        session.close()


if __name__ == "__main__":
    main()
