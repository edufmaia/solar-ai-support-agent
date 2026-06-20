from pydantic import BaseModel, ConfigDict


class ChatwootRef(BaseModel):
    """Reference object (conversation/account) — only the id is needed."""

    model_config = ConfigDict(extra="ignore")

    id: int


class ChatwootWebhookEvent(BaseModel):
    """Lenient model of a Chatwoot webhook payload (e.g. message_created)."""

    model_config = ConfigDict(extra="ignore")

    event: str
    message_type: str | None = None
    content: str | None = None
    conversation: ChatwootRef | None = None
    account: ChatwootRef | None = None
