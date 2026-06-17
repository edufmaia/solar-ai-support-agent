from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    lead_id: UUID | None = None
    channel: str | None = None
    status: str | None = None
    current_state: str | None = None
    assigned_to_human: bool = False


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None = None
    channel: str | None = None
    status: str | None = None
    current_state: str | None = None
    assigned_to_human: bool
    started_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
