import io
import re
from uuid import UUID, uuid4

from docx import Document
from pypdf import PdfReader

from ..config.settings import get_settings
from ..schemas.knowledge import KnowledgeIngestResult

_WS = re.compile(r"[ \t]+")
_NL = re.compile(r"\n{3,}")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class DocumentParseError(Exception):
    """Raised when an uploaded document cannot be turned into text."""


def _normalize(text: str) -> str:
    text = _CTRL.sub("", text)
    text = _WS.sub(" ", text)
    text = _NL.sub("\n\n", text)
    return text.strip()


def extract_text(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
    elif name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:  # noqa: BLE001 - any pypdf error means parse failure
            raise DocumentParseError(f"Falha ao ler o PDF: {exc}") from exc
    elif name.endswith(".docx"):
        try:
            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:  # noqa: BLE001
            raise DocumentParseError(f"Falha ao ler o DOCX: {exc}") from exc
    else:
        raise DocumentParseError(
            "Formato não suportado. Use PDF, DOCX, TXT ou MD (ou cole o texto)."
        )

    text = _normalize(text)
    if not text:
        raise DocumentParseError(
            "Nenhum texto extraível. Para PDF, use um arquivo pesquisável (não digitalizado)."
        )
    return text


def chunk_text(text: str, size: int, overlap: int, max_chunks: int) -> tuple[list[str], bool]:
    text = text.strip()
    if not text:
        return [], False
    chunks: list[str] = []
    start = 0
    n = len(text)
    step = max(1, size - overlap)
    while start < n:
        end = min(start + size, n)
        if end < n:
            window = text[start:end]
            for sep in ("\n\n", ". ", "\n", " "):
                idx = window.rfind(sep)
                if idx > size // 2:
                    end = start + idx + len(sep)
                    break
        chunks.append(text[start:end].strip())
        if len(chunks) >= max_chunks:
            return chunks, end < n
        start = max(start + step, end - overlap)
    return [c for c in chunks if c], False


def ingest(
    *,
    title: str,
    category: str | None,
    source: str | None,
    file_bytes: bytes | None = None,
    filename: str | None = None,
    pasted_text: str | None = None,
) -> tuple[list[str], KnowledgeIngestResult]:
    """Parse + chunk a document. Returns the chunks plus a summary.

    Persistence is done by the caller (the API layer) via the repository.
    """
    settings = get_settings()
    if file_bytes is not None:
        max_bytes = settings.knowledge_max_file_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise DocumentParseError(
                f"Arquivo maior que o limite de {settings.knowledge_max_file_mb} MB."
            )
        text = extract_text(filename or "", file_bytes)
    elif pasted_text and pasted_text.strip():
        text = _normalize(pasted_text)
    else:
        raise DocumentParseError("Envie um arquivo ou cole um texto.")

    chunks, truncated = chunk_text(
        text,
        size=settings.knowledge_chunk_size,
        overlap=settings.knowledge_chunk_overlap,
        max_chunks=settings.knowledge_max_chunks,
    )
    if not chunks:
        raise DocumentParseError("Documento sem conteúdo após processamento.")
    group_id: UUID = uuid4()
    result = KnowledgeIngestResult(
        document_group_id=group_id,
        chunk_count=len(chunks),
        source=source,
        truncated=truncated,
    )
    return chunks, result
