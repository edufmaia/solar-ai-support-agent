from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class KnowledgeSnippet(BaseModel):
    content: str
    source: str | None = None


class KnowledgeDocumentGroup(BaseModel):
    document_group_id: UUID
    title: str
    source: str | None = None
    category: str | None = None
    chunk_count: int
    is_active: bool
    updated_at: datetime


class KnowledgeIngestResult(BaseModel):
    document_group_id: UUID
    chunk_count: int
    source: str | None = None
    truncated: bool = False
