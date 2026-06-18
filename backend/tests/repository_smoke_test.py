from decimal import Decimal
from pathlib import Path
import sys
from uuid import UUID
import uuid

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config.database import SessionLocal
from app.repositories import ConversationRepository, LeadRepository, MessageRepository
from app.schemas import ConversationCreate, LeadCreate, MessageCreate


def main() -> None:
    session = SessionLocal()
    lead_id: UUID | None = None
    conversation_id: UUID | None = None
    suffix = uuid.uuid4().hex[:8]

    lead_repository = LeadRepository(session)
    conversation_repository = ConversationRepository(session)
    message_repository = MessageRepository(session)

    try:
        created_lead = lead_repository.create(
            LeadCreate(
                name=f"Smoke Test Lead {suffix}",
                phone=f"+5500000{suffix}",
                email=f"smoke-{suffix}@example.com",
                city="Natal",
                state="RN",
                address="Rua Exemplo, 123",
                property_type="residential",
                average_energy_bill=Decimal("350.50"),
                intent="quote",
                source_channel="smoke-test",
            )
        )
        lead_id = created_lead.id
        assert created_lead.phone is not None

        fetched_lead = lead_repository.get_by_id(lead_id)
        assert fetched_lead is not None
        assert fetched_lead.id == lead_id

        fetched_by_phone = lead_repository.get_by_phone(created_lead.phone)
        assert fetched_by_phone is not None
        assert fetched_by_phone.id == lead_id

        updated_lead = lead_repository.update_score(lead_id, 82, "hot")
        assert updated_lead is not None
        assert updated_lead.lead_score == 82
        assert updated_lead.lead_temperature == "hot"

        created_conversation = conversation_repository.create(
            ConversationCreate(
                lead_id=lead_id,
                channel="whatsapp",
                status="active",
                current_state="collecting_profile",
                assigned_to_human=False,
            )
        )
        conversation_id = created_conversation.id

        fetched_conversation = conversation_repository.get_by_id(conversation_id)
        assert fetched_conversation is not None
        assert fetched_conversation.id == conversation_id

        lead_conversations = conversation_repository.get_by_lead_id(lead_id)
        assert any(conversation.id == conversation_id for conversation in lead_conversations)

        updated_conversation = conversation_repository.update_state(
            conversation_id,
            "awaiting_energy_bill",
        )
        assert updated_conversation is not None
        assert updated_conversation.current_state == "awaiting_energy_bill"

        handed_off = conversation_repository.mark_handoff(conversation_id)
        assert handed_off is not None
        assert handed_off.assigned_to_human is True
        assert handed_off.status == "waiting_human"

        flagged_lead = lead_repository.update_status(lead_id, "handoff_requested")
        assert flagged_lead is not None
        assert flagged_lead.status == "handoff_requested"

        first_message = message_repository.create(
            MessageCreate(
                conversation_id=conversation_id,
                role="user",
                content="Tenho interesse em energia solar.",
                model_provider=None,
                model_name=None,
                input_tokens=None,
                output_tokens=None,
                estimated_cost=None,
            )
        )

        second_message = message_repository.create(
            MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content="Perfeito! Vou coletar algumas informações iniciais.",
                model_provider="mock",
                model_name="mock-reply-v1",
                input_tokens=12,
                output_tokens=18,
                estimated_cost=Decimal("0.000123"),
            )
        )

        fetched_message = message_repository.get_by_id(first_message.id)
        assert fetched_message is not None
        assert fetched_message.id == first_message.id

        conversation_messages = message_repository.list_by_conversation_id(conversation_id)
        assert len(conversation_messages) >= 2
        assert conversation_messages[0].conversation_id == conversation_id

        closed_conversation = conversation_repository.close(conversation_id)
        assert closed_conversation is not None
        assert closed_conversation.status == "closed"
        assert closed_conversation.closed_at is not None

        print("Repository smoke test passed.")
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
