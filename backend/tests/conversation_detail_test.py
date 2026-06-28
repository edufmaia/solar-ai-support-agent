"""Integration check for the T025 conversation-detail endpoint/service.

Drives two turns (lead data, then consent + address) against real Postgres +
Redis and asserts the consolidated detail exposes the scored lead, the solar
pre-analysis (panel range) and the handoff state — the data the UI inspector
renders. Cleans up. Run inside the container:

    docker compose -p solar-ai-support-agent exec backend python tests/conversation_detail_test.py
"""

import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.orchestrator import MockAgentOrchestrator
from app.config.database import SessionLocal
from app.config.redis_client import get_redis_client
from app.schemas.chat import ChatRequest
from app.services.conversation_detail_service import ConversationDetailService


def main() -> None:
    session = SessionLocal()
    conversation_id: UUID | None = None
    lead_id: UUID | None = None

    try:
        orchestrator = MockAgentOrchestrator(session)

        first = orchestrator.handle_chat(
            ChatRequest(
                message=(
                    "Olá, sou o Tiago de Natal, moro na Rua das Acácias, 250, "
                    "minha conta vem R$ 800 e quero energia solar na minha casa"
                ),
                channel="api",
            )
        )
        conversation_id = first.conversation_id

        orchestrator.handle_chat(
            ChatRequest(
                message="Autorizo a análise, pode verificar meu endereço.",
                conversation_id=conversation_id,
                channel="api",
            )
        )

        detail = ConversationDetailService(session).build(conversation_id)
        assert detail is not None
        lead_id = detail.conversation.lead_id

        # Lead was scored.
        assert detail.lead is not None
        assert detail.lead.lead_score is not None
        assert detail.lead.lead_temperature in {"cold", "warm", "hot"}

        # Solar pre-analysis populated with a panel range (what the UI shows).
        assert detail.geospatial is not None
        assert detail.geospatial.solar_data_available is True
        assert detail.geospatial.estimated_panel_min is not None
        assert detail.geospatial.estimated_panel_max is not None

        # Transcript present: both user messages and at least one assistant reply.
        assert len(detail.messages) >= 3
        roles = {m.role for m in detail.messages}
        assert "user" in roles and "assistant" in roles
        assert all(m.content for m in detail.messages)
        assert not hasattr(detail, "events")

        print("Conversation-detail integration test passed.")
        print(
            f"  lead: score={detail.lead.lead_score} temp={detail.lead.lead_temperature} "
            f"handoff={detail.conversation.assigned_to_human}"
        )
        print(
            f"  solar: {detail.geospatial.estimated_panel_min}-"
            f"{detail.geospatial.estimated_panel_max} placas, "
            f"{detail.geospatial.estimated_system_kwp} kWp, "
            f"revisao_tecnica={detail.geospatial.requires_technical_review}"
        )
    finally:
        if conversation_id is not None:
            get_redis_client().delete(f"session:{conversation_id}")
            session.execute(
                text("DELETE FROM conversations WHERE id = :cid"),
                {"cid": conversation_id},
            )
            session.commit()
        if lead_id is not None:
            session.execute(text("DELETE FROM leads WHERE id = :lid"), {"lid": lead_id})
            session.commit()
        session.close()


if __name__ == "__main__":
    main()
