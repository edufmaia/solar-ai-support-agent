"""Integration check for the T021 Redis session cache.

Runs two turns on the same conversation against real Redis + Postgres and
asserts the ephemeral session is created on turn 1 and recovered on turn 2
(turn_count increments, session_recovered event emitted). Cleans up the
Postgres rows and the Redis key. Run inside the container:

    docker compose -p solar-ai-support-agent exec backend python tests/session_test.py
"""

from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.orchestrator import MockAgentOrchestrator
from app.config.database import SessionLocal
from app.config.redis_client import get_redis_client
from app.repositories import AgentEventRepository, ConversationRepository
from app.schemas.chat import ChatRequest
from app.session import build_session_store


def main() -> None:
    session = SessionLocal()
    store = build_session_store()
    redis_client = get_redis_client()
    conversation_id: UUID | None = None
    lead_id: UUID | None = None

    try:
        orchestrator = MockAgentOrchestrator(session, session_store=store)

        # Turn 1 — new conversation: session created, no recovery event.
        first = orchestrator.handle_chat(
            ChatRequest(
                message="Olá, sou o Carlos de Natal, minha conta é R$ 480.",
                channel="api",
            )
        )
        conversation_id = first.conversation_id
        conversation = ConversationRepository(session).get_by_id(conversation_id)
        assert conversation is not None
        lead_id = conversation.lead_id

        events_after_first = AgentEventRepository(session).list_by_conversation_id(conversation_id)
        assert not any(e.event_type == "session_recovered" for e in events_after_first)

        state1 = store.get(conversation_id)
        assert state1 is not None
        assert state1.turn_count == 1

        key = f"session:{conversation_id}"
        assert redis_client.ttl(key) > 0  # TTL applied

        # Turn 2 — same conversation: session recovered, turn_count increments.
        orchestrator.handle_chat(
            ChatRequest(
                message="Quero saber mais sobre energia solar.",
                conversation_id=conversation_id,
                channel="api",
            )
        )

        events_after_second = AgentEventRepository(session).list_by_conversation_id(conversation_id)
        assert any(e.event_type == "session_recovered" for e in events_after_second)

        state2 = store.get(conversation_id)
        assert state2 is not None
        assert state2.turn_count == 2

        print("Redis session integration test passed.")
    finally:
        if conversation_id is not None:
            redis_client.delete(f"session:{conversation_id}")
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
