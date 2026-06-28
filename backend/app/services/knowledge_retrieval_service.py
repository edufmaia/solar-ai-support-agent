from sqlalchemy.orm import Session

from ..config.settings import get_settings
from ..repositories.knowledge_document_repository import KnowledgeDocumentRepository
from ..schemas.knowledge import KnowledgeSnippet


class KnowledgeRetrievalService:
    def __init__(self, session: Session) -> None:
        self.repository = KnowledgeDocumentRepository(session)
        self.settings = get_settings()

    def retrieve(self, query_text: str) -> list[KnowledgeSnippet]:
        if not query_text or not query_text.strip():
            return []
        return self.repository.search(
            query_text,
            limit=self.settings.knowledge_top_k,
            min_rank=self.settings.knowledge_min_rank,
        )
