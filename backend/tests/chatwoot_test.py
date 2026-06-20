"""Integration check for the T022 Chatwoot webhook.

Drives ChatwootWebhookService against real Postgres + Redis (no live Chatwoot,
so the reply send fails gracefully) and asserts an incoming message creates a
`chatwoot` conversation, a second message on the same Chatwoot conversation
reuses it (continuity via Redis), and outgoing/echo events are ignored. Cleans
up Postgres rows and the Redis keys. Run inside the container:

    docker compose -p solar-ai-support-agent exec backend python tests/chatwoot_test.py
"""

from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config.database import SessionLocal
from app.config.redis_client import get_redis_client
from app.repositories import ConversationRepository
from app.schemas.chatwoot import ChatwootRef, ChatwootWebhookEvent
from app.services.chatwoot_webhook_service import ChatwootWebhookService

ACCOUNT_ID = 1
CW_CONVERSATION_ID = 999001


def _incoming(content: str) -> ChatwootWebhookEvent:
    return ChatwootWebhookEvent(
        event="message_created",
        message_type="incoming",
        content=content,
        conversation=ChatwootRef(id=CW_CONVERSATION_ID),
        account=ChatwootRef(id=ACCOUNT_ID),
    )


def main() -> None:
    session = SessionLocal()
    redis_client = get_redis_client()
    conversation_id: UUID | None = None
    lead_id: UUID | None = None

    try:
        service = ChatwootWebhookService(session)

        out1 = service.handle(_incoming("Olá, sou o Rui de Natal, conta R$ 470."))
        assert out1["status"] == "handled", out1
        # No live Chatwoot configured in this environment -> reply not sent.
        assert out1["reply_sent"] is False
        conversation_id = UUID(out1["conversation_id"])

        conversation = ConversationRepository(session).get_by_id(conversation_id)
        assert conversation is not None
        assert conversation.channel == "chatwoot"
        lead_id = conversation.lead_id

        # Second incoming on the same Chatwoot conversation -> same internal one.
        out2 = service.handle(_incoming("Quero saber sobre energia solar."))
        assert out2["conversation_id"] == out1["conversation_id"]

        # Outgoing (our own echo) must be ignored to avoid loops.
        out3 = service.handle(
            ChatwootWebhookEvent(
                event="message_created",
                message_type="outgoing",
                content="resposta do bot",
                conversation=ChatwootRef(id=CW_CONVERSATION_ID),
                account=ChatwootRef(id=ACCOUNT_ID),
            )
        )
        assert out3["status"] == "ignored"

        print("Chatwoot webhook integration test passed.")
    finally:
        redis_client.delete(f"chatwoot:{ACCOUNT_ID}:{CW_CONVERSATION_ID}")
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
