from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    conversation_id: UUID
    user_message: str
    current_state: str | None = None
    lead_data: dict[str, Any] | None = None
    lead_score: int | None = None
    lead_temperature: str | None = None
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    geospatial: dict[str, Any] | None = None
    history: list[dict[str, str]] | None = None
    system_prompt: str | None = None
    knowledge: list[dict[str, Any]] = Field(default_factory=list)


class LLMResponse(BaseModel):
    content: str
    provider: str
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: Decimal = Decimal("0")
    raw_response: dict[str, Any] = Field(default_factory=dict)
    next_state: str | None = None
