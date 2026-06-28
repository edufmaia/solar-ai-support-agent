from uuid import UUID

from sqlalchemy.orm import Session

from ..repositories import (
    ConversationRepository,
    GeospatialAnalysisRepository,
    LeadRepository,
    MessageRepository,
)
from ..schemas.conversation_detail import ConversationDetail


class ConversationDetailService:
    """Read-only consolidated view of a conversation for the admin panel."""

    def __init__(self, session: Session) -> None:
        self.conversation_repository = ConversationRepository(session)
        self.lead_repository = LeadRepository(session)
        self.geospatial_analysis_repository = GeospatialAnalysisRepository(session)
        self.message_repository = MessageRepository(session)

    def build(self, conversation_id: UUID) -> ConversationDetail | None:
        conversation = self.conversation_repository.get_by_id(conversation_id)
        if conversation is None:
            return None

        lead = None
        geospatial = None
        if conversation.lead_id is not None:
            lead = self.lead_repository.get_by_id(conversation.lead_id)
            geospatial = self.geospatial_analysis_repository.get_latest_by_lead_id(
                conversation.lead_id
            )

        messages = self.message_repository.list_by_conversation_id(conversation_id)

        return ConversationDetail(
            conversation=conversation,
            lead=lead,
            geospatial=geospatial,
            messages=messages,
        )
