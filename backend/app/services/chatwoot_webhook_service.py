from typing import Any

from sqlalchemy.orm import Session

from ..agents.orchestrator import MockAgentOrchestrator
from ..integrations.chatwoot import (
    ChatwootClient,
    ChatwootConversationMap,
    ChatwootError,
    build_chatwoot_client,
    build_chatwoot_conversation_map,
)
from ..schemas.chat import ChatRequest
from ..schemas.chatwoot import ChatwootWebhookEvent

INCOMING_EVENT = "message_created"
INCOMING_MESSAGE_TYPE = "incoming"


class ChatwootWebhookService:
    """Turns an incoming Chatwoot message into an agent reply.

    Filters to incoming `message_created` events, runs the orchestrator
    (reusing the mapped conversation for continuity) and replies via the
    Chatwoot API. Always acks: a failed reply does not raise.
    """

    def __init__(
        self,
        session: Session,
        orchestrator: MockAgentOrchestrator | None = None,
        client: ChatwootClient | None = None,
        conversation_map: ChatwootConversationMap | None = None,
    ) -> None:
        self.orchestrator = orchestrator or MockAgentOrchestrator(session)
        self.client = client or build_chatwoot_client()
        self.conversation_map = conversation_map or build_chatwoot_conversation_map()

    def handle(self, event: ChatwootWebhookEvent) -> dict[str, Any]:
        if event.event != INCOMING_EVENT:
            return {"status": "ignored", "reason": "event"}
        if event.message_type != INCOMING_MESSAGE_TYPE:
            return {"status": "ignored", "reason": "message_type"}
        if not event.content or not event.content.strip():
            return {"status": "ignored", "reason": "empty_content"}
        if event.conversation is None or event.account is None:
            return {"status": "ignored", "reason": "missing_refs"}

        account_id = event.account.id
        cw_conversation_id = event.conversation.id

        our_id = self.conversation_map.get(account_id, cw_conversation_id)
        result = self.orchestrator.handle_chat(
            ChatRequest(
                message=event.content,
                conversation_id=our_id,
                channel="chatwoot",
            )
        )
        self.conversation_map.set(account_id, cw_conversation_id, result.conversation_id)

        response: dict[str, Any] = {
            "status": "handled",
            "conversation_id": str(result.conversation_id),
        }
        try:
            self.client.send_message(account_id, cw_conversation_id, result.response)
            response["reply_sent"] = True
        except ChatwootError as exc:
            response["reply_sent"] = False
            response["reply_error"] = str(exc)
        return response
