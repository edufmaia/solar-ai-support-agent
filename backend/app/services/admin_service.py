from sqlalchemy.orm import Session

from ..repositories import ConversationRepository
from ..schemas.admin import ConversationListResponse

MAX_LIMIT = 100


class AdminService:
    """Read-only aggregations for the admin panel."""

    def __init__(self, session: Session) -> None:
        self.conversation_repository = ConversationRepository(session)

    def list_conversations(self, limit: int, offset: int) -> ConversationListResponse:
        limit = max(1, min(int(limit), MAX_LIMIT))
        offset = max(0, int(offset))
        items = self.conversation_repository.list_with_lead(limit, offset)
        total = self.conversation_repository.count_all()
        return ConversationListResponse(
            items=items, total=total, limit=limit, offset=offset
        )
