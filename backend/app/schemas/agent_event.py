from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentEventCreate(BaseModel):
    conversation_id: UUID
    lead_id: UUID | None = None
    event_type: str
    event_source: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    lead_id: UUID | None = None
    event_type: str
    event_source: str
    payload: dict[str, Any]
    created_at: datetime
