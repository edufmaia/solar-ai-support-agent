from ..repositories.conversation_repository import ConversationRepository
from ..repositories.lead_repository import LeadRepository
from ..schemas.conversation import ConversationRead
from ..schemas.tools import RequestHumanHandoffInput
from .base import AgentTool


class RequestHumanHandoffTool(AgentTool[RequestHumanHandoffInput]):
    name = "request_human_handoff"
    description = (
        "Encaminha a conversa para atendimento humano e marca o lead como handoff solicitado."
    )
    input_model = RequestHumanHandoffInput

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        lead_repository: LeadRepository,
    ) -> None:
        self.conversation_repository = conversation_repository
        self.lead_repository = lead_repository

    def execute(self, payload: RequestHumanHandoffInput) -> ConversationRead | None:
        conversation = self.conversation_repository.mark_handoff(payload.conversation_id)
        if payload.lead_id is not None:
            self.lead_repository.update_status(payload.lead_id, "handoff_requested")
        return conversation
