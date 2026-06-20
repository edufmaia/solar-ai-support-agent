from pydantic import BaseModel, Field

from .agent_event import AgentEventRead
from .conversation import ConversationRead
from .geospatial import GeospatialAnalysisRead
from .lead import LeadRead


class ConversationDetail(BaseModel):
    conversation: ConversationRead
    lead: LeadRead | None = None
    geospatial: GeospatialAnalysisRead | None = None
    events: list[AgentEventRead] = Field(default_factory=list)
