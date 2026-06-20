"""Integration check for the T019 consolidated turn event.

Drives MockAgentOrchestrator.handle_chat against a real database (mock LLM
provider) and asserts that a single `agent_turn_completed` event closes the
turn with consolidated cost/token data and an accurate event count. Cleans up
the lead/conversation it creates. Run inside the backend container:

    docker compose -p solar-ai-support-agent exec backend python tests/agent_turn_event_test.py
"""

from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.orchestrator import MockAgentOrchestrator
from app.config.database import SessionLocal
from app.repositories import AgentEventRepository, ConversationRepository
from app.schemas.chat import ChatRequest


def main() -> None:
    session = SessionLocal()
    conversation_id: UUID | None = None
    lead_id: UUID | None = None

    try:
        orchestrator = MockAgentOrchestrator(session)
        response = orchestrator.handle_chat(
            ChatRequest(
                message="Olá, meu nome é Maria, moro em Natal e minha conta de luz é R$ 450.",
                channel="api",
            )
        )
        conversation_id = response.conversation_id

        conversation = ConversationRepository(session).get_by_id(conversation_id)
        assert conversation is not None
        lead_id = conversation.lead_id

        events = AgentEventRepository(session).list_by_conversation_id(conversation_id)
        assert events, "expected at least one agent event"

        last = events[-1]
        assert last.event_type == "agent_turn_completed", last.event_type

        payload = last.payload
        assert payload["provider"] == "mock"
        assert payload["total_tokens"] == payload["input_tokens"] + payload["output_tokens"]
        assert payload["estimated_cost"] == 0.0
        # events_recorded counts every event before the consolidated one
        assert payload["events_recorded"] == len(events) - 1
        assert payload["events_recorded"] > 0

        # exactly one consolidated event per turn
        completed = [e for e in events if e.event_type == "agent_turn_completed"]
        assert len(completed) == 1

        print("Agent turn-event integration test passed.")
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
