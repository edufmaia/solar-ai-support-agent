from decimal import Decimal

from pydantic import BaseModel, Field


class UsageByModel(BaseModel):
    model_provider: str | None = None
    model_name: str | None = None
    message_count: int
    input_tokens: int
    output_tokens: int
    estimated_cost: Decimal


class UsageAggregate(BaseModel):
    total_messages: int
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost: Decimal
    by_model: list[UsageByModel] = Field(default_factory=list)
