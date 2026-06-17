from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: UUID | None = None
    channel: str | None = "api"


class ChatResponse(BaseModel):
    conversation_id: UUID
    response: str
    mode: str = "mock"
