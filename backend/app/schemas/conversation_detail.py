from pydantic import BaseModel, Field

from .conversation import ConversationRead
from .geospatial import GeospatialAnalysisRead
from .lead import LeadRead
from .message import MessageRead


class ConversationDetail(BaseModel):
    conversation: ConversationRead
    lead: LeadRead | None = None
    geospatial: GeospatialAnalysisRead | None = None
    messages: list[MessageRead] = Field(default_factory=list)
