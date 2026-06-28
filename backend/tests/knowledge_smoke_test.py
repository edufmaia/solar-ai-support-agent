"""Knowledge base + agent settings smoke test (requires a running, schema-applied DB)."""

import sys
from pathlib import Path
from uuid import uuid4

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config.database import SessionLocal  # noqa: E402
from app.repositories.agent_settings_repository import AgentSettingsRepository  # noqa: E402
from app.repositories.knowledge_document_repository import (  # noqa: E402
    KnowledgeDocumentRepository,
)


def main() -> None:
    session = SessionLocal()
    try:
        kb = KnowledgeDocumentRepository(session)
        settings_repo = AgentSettingsRepository(session)

        gid = uuid4()
        kb.insert_chunks(
            gid,
            title="Política comercial",
            source="politica.txt",
            category="comercial",
            chunks=[
                "A garantia dos painéis solares é de 25 anos.",
                "O financiamento pode ser parcelado em até 60 vezes.",
            ],
        )

        groups = kb.list_groups()
        assert any(g.document_group_id == gid and g.chunk_count == 2 for g in groups)

        hits = kb.search("garantia dos painéis", limit=4, min_rank=0.0)
        assert any("garantia" in h.content.lower() for h in hits), "FTS should find the chunk"

        # Realistic question (extra words not in the doc) must still match via OR query.
        q_hits = kb.search(
            "qual a garantia dos painéis e em quantas vezes posso parcelar?",
            limit=4,
            min_rank=0.0,
        )
        assert any("garantia" in h.content.lower() for h in q_hits), (
            "question-style query should still retrieve the chunk (OR semantics)"
        )

        kb.set_active(gid, False)
        assert kb.search("garantia dos painéis", limit=4, min_rank=0.0) == []
        kb.set_active(gid, True)

        settings_repo.update(system_prompt="Prompt de teste", knowledge_enabled=False)
        s = settings_repo.get()
        assert s.system_prompt == "Prompt de teste" and s.knowledge_enabled is False
        settings_repo.reset_prompt()
        assert settings_repo.get().system_prompt is None
        settings_repo.update(system_prompt=None, knowledge_enabled=True)

        deleted = kb.delete_group(gid)
        assert deleted == 2
        print("knowledge_smoke_test OK")
    finally:
        session.close()


if __name__ == "__main__":
    main()
