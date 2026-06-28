from uuid import uuid4

from app.llm.context import build_response_context_block
from app.schemas.llm import LLMRequest


def _req(**kw):
    return LLMRequest(conversation_id=uuid4(), user_message="oi", **kw)


def test_context_block_includes_knowledge_section():
    req = _req(
        knowledge=[
            {"content": "Garantia de 25 anos.", "source": "politica.docx"},
            {"content": "Financiamento em 60x.", "source": "precos.pdf"},
        ]
    )
    block = build_response_context_block(req)
    assert "Base de conhecimento da empresa" in block
    assert "Garantia de 25 anos." in block
    assert "[origem: politica.docx]" in block


def test_context_block_without_knowledge_has_no_section():
    block = build_response_context_block(_req())
    assert "Base de conhecimento" not in block
