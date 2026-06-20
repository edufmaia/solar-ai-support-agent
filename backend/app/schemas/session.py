from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SessionState(BaseModel):
    conversation_id: UUID
    current_state: str | None = None
    lead_id: UUID | None = None
    lead_score: int | None = None
    lead_temperature: str | None = None
    turn_count: int = 0
    updated_at: datetime
