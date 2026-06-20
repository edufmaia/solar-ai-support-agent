from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db_session
from ..schemas.chatwoot import ChatwootWebhookEvent
from ..services.chatwoot_webhook_service import ChatwootWebhookService

router = APIRouter(tags=["chatwoot"])


@router.post("/webhooks/chatwoot")
def chatwoot_webhook(
    event: ChatwootWebhookEvent,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    return ChatwootWebhookService(session).handle(event)
