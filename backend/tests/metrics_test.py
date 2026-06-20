"""Integration check for the T020 metrics aggregation.

Runs a chat turn against a real database (mock LLM provider), builds the
MetricsService, and asserts the aggregated leads / conversations / usage /
events. Cleans up the lead/conversation it creates. Run inside the container:

    docker compose -p solar-ai-support-agent exec backend python tests/metrics_test.py
"""

from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.orchestrator import MockAgentOrchestrator
from app.config.database import SessionLocal
from app.repositories import ConversationRepository
from app.schemas.chat import ChatRequest
from app.services.metrics_service import MetricsService


def main() -> None:
    session = SessionLocal()
    conversation_id: UUID | None = None
    lead_id: UUID | None = None

    try:
        orchestrator = MockAgentOrchestrator(session)
        response = orchestrator.handle_chat(
            ChatRequest(
                message="Olá, sou a Ana de Mossoró, minha conta de luz é R$ 600.",
                channel="api",
            )
        )
        conversation_id = response.conversation_id
        conversation = ConversationRepository(session).get_by_id(conversation_id)
        assert conversation is not None
        lead_id = conversation.lead_id

        metrics = MetricsService(session).build()

        assert metrics.leads.total >= 1
        assert sum(metrics.leads.by_temperature.values()) == metrics.leads.total

        assert metrics.conversations.total >= 1
        assert metrics.conversations.assigned_to_human >= 0

        assert metrics.usage.total_messages >= 2  # user + assistant

        event_types = {entry.event_type: entry.count for entry in metrics.events}
        assert event_types.get("agent_turn_completed", 0) >= 1

        print("Metrics integration test passed.")
    finally:
        if conversation_id is not None:
            session.execute(
                text("DELETE FROM conversations WHERE id = :conversation_id"),
                {"conversation_id": conversation_id},
            )
            session.commit()
        if lead_id is not None:
            session.execute(
                text("DELETE FROM leads WHERE id = :lead_id"),
                {"lead_id": lead_id},
            )
            session.commit()
        session.close()


if __name__ == "__main__":
    main()
