from pydantic import BaseModel, Field

from .usage import UsageAggregate


class EventTypeCount(BaseModel):
    event_type: str
    count: int


class LeadMetrics(BaseModel):
    total: int
    by_temperature: dict[str, int] = Field(default_factory=dict)


class ConversationMetrics(BaseModel):
    total: int
    assigned_to_human: int


class MetricsResponse(BaseModel):
    leads: LeadMetrics
    conversations: ConversationMetrics
    usage: UsageAggregate
    events: list[EventTypeCount] = Field(default_factory=list)
