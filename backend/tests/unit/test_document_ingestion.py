import io

import pytest
from app.services.document_ingestion_service import (
    DocumentParseError,
    chunk_text,
    extract_text,
    ingest,
)


def test_chunk_short_text_single_chunk():
    chunks, truncated = chunk_text("Texto curto.", size=800, overlap=100, max_chunks=400)
    assert chunks == ["Texto curto."]
    assert truncated is False


def test_chunk_respects_size_and_overlap():
    text = "a" * 2000
    chunks, truncated = chunk_text(text, size=800, overlap=100, max_chunks=400)
    assert len(chunks) >= 3
    assert all(len(c) <= 800 for c in chunks)
    assert chunks[0][-50:] in chunks[1]
    assert truncated is False


def test_chunk_truncates_at_max_chunks():
    text = "palavra " * 5000
    chunks, truncated = chunk_text(text, size=100, overlap=0, max_chunks=5)
    assert len(chunks) == 5
    assert truncated is True


def test_extract_txt():
    assert "olá mundo" in extract_text("notas.txt", "olá mundo".encode()).lower()


def test_extract_unsupported_extension_raises():
    with pytest.raises(DocumentParseError):
        extract_text("planilha.xlsx", b"...")


def test_extract_docx_roundtrip():
    from docx import Document

    doc = Document()
    doc.add_paragraph("Política de garantia: 25 anos para os painéis.")
    buf = io.BytesIO()
    doc.save(buf)
    out = extract_text("politica.docx", buf.getvalue())
    assert "garantia" in out.lower()


def test_extract_pdf_uses_pypdf(monkeypatch):
    class _FakePage:
        def extract_text(self):
            return "Tabela de preços 2026"

    class _FakeReader:
        def __init__(self, *_args, **_kwargs):
            self.pages = [_FakePage()]

    monkeypatch.setattr("app.services.document_ingestion_service.PdfReader", _FakeReader)
    out = extract_text("precos.pdf", b"%PDF-fake")
    assert "preços" in out.lower()


def test_ingest_pasted_text():
    chunks, result = ingest(
        title="Política",
        category="comercial",
        source="texto colado",
        pasted_text="A garantia dos painéis é de 25 anos.",
    )
    assert chunks and "garantia" in chunks[0].lower()
    assert result.chunk_count == len(chunks)
    assert result.source == "texto colado"


def test_ingest_file_bytes_txt():
    chunks, result = ingest(
        title="Notas",
        category=None,
        source="notas.txt",
        file_bytes=b"financiamento em 60x",
        filename="notas.txt",
    )
    assert result.chunk_count == 1
    assert "financiamento" in chunks[0].lower()


def test_ingest_rejects_oversized_file():
    big = b"a" * (10 * 1024 * 1024 + 1)
    with pytest.raises(DocumentParseError):
        ingest(title="X", category=None, source="big.txt", file_bytes=big, filename="big.txt")


def test_ingest_requires_content():
    with pytest.raises(DocumentParseError):
        ingest(title="X", category=None, source=None, pasted_text="   ")
