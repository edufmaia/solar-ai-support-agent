from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config.database import get_db_session
from ..schemas.conversation_detail import ConversationDetail
from ..services.conversation_detail_service import ConversationDetailService

router = APIRouter(tags=["conversations"])


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID,
    session: Session = Depends(get_db_session),
) -> ConversationDetail:
    detail = ConversationDetailService(session).build(conversation_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found",
        )
    return detail
