from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    system_prompt: str | None = None
    knowledge_enabled: bool = True
    updated_at: datetime


class AgentSettingsUpdate(BaseModel):
    system_prompt: str | None = None
    knowledge_enabled: bool | None = None
