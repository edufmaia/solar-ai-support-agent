from sqlalchemy.orm import Session

from ..repositories import (
    AgentEventRepository,
    ConversationRepository,
    LeadRepository,
    MessageRepository,
)
from ..schemas.metrics import MetricsResponse


class MetricsService:
    """Assemble aggregated agent metrics from the repositories (read-only)."""

    def __init__(self, session: Session) -> None:
        self.lead_repository = LeadRepository(session)
        self.conversation_repository = ConversationRepository(session)
        self.message_repository = MessageRepository(session)
        self.agent_event_repository = AgentEventRepository(session)

    def build(self) -> MetricsResponse:
        return MetricsResponse(
            leads=self.lead_repository.metrics(),
            conversations=self.conversation_repository.metrics(),
            usage=self.message_repository.aggregate_usage(),
            events=self.agent_event_repository.count_by_event_type(),
        )
