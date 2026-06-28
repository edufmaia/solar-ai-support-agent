from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..schemas.knowledge import KnowledgeDocumentGroup, KnowledgeSnippet


class KnowledgeDocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_chunks(
        self,
        group_id: UUID,
        title: str,
        source: str | None,
        category: str | None,
        chunks: list[str],
    ) -> int:
        try:
            for i, content in enumerate(chunks):
                self.session.execute(
                    text(
                        "INSERT INTO knowledge_documents "
                        "(title, content, source, category, is_active, "
                        " document_group_id, chunk_index) "
                        "VALUES (:title, :content, :source, :category, TRUE, "
                        " :gid, :idx)"
                    ),
                    {
                        "title": title,
                        "content": content,
                        "source": source,
                        "category": category,
                        "gid": str(group_id),
                        "idx": i,
                    },
                )
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        return len(chunks)

    def list_groups(self) -> list[KnowledgeDocumentGroup]:
        rows = (
            self.session.execute(
                text(
                    "SELECT document_group_id, MIN(title) AS title, "
                    "MIN(source) AS source, MIN(category) AS category, "
                    "COUNT(*) AS chunk_count, bool_or(is_active) AS is_active, "
                    "MAX(updated_at) AS updated_at "
                    "FROM knowledge_documents WHERE document_group_id IS NOT NULL "
                    "GROUP BY document_group_id ORDER BY MAX(updated_at) DESC"
                )
            )
            .mappings()
            .all()
        )
        return [KnowledgeDocumentGroup.model_validate(dict(r)) for r in rows]

    def set_active(self, group_id: UUID, is_active: bool) -> int:
        try:
            result = cast(
                "CursorResult[Any]",
                self.session.execute(
                    text(
                        "UPDATE knowledge_documents SET is_active = :active, "
                        "updated_at = now() WHERE document_group_id = :gid"
                    ),
                    {"active": is_active, "gid": str(group_id)},
                ),
            )
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        return result.rowcount

    def delete_group(self, group_id: UUID) -> int:
        try:
            result = cast(
                "CursorResult[Any]",
                self.session.execute(
                    text("DELETE FROM knowledge_documents WHERE document_group_id = :gid"),
                    {"gid": str(group_id)},
                ),
            )
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        return result.rowcount

    def search(self, query: str, limit: int, min_rank: float) -> list[KnowledgeSnippet]:
        rows = (
            self.session.execute(
                text(
                    "SELECT content, source, "
                    "ts_rank(to_tsvector('simple', coalesce(title,'') || ' ' || "
                    "coalesce(content,'')), plainto_tsquery('simple', :q)) AS rank "
                    "FROM knowledge_documents "
                    "WHERE is_active = TRUE "
                    "AND to_tsvector('simple', coalesce(title,'') || ' ' || "
                    "coalesce(content,'')) @@ plainto_tsquery('simple', :q) "
                    "ORDER BY rank DESC LIMIT :limit"
                ),
                {"q": query, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [
            KnowledgeSnippet(content=r["content"], source=r["source"])
            for r in rows
            if r["rank"] >= min_rank
        ]
