from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from ..config.database import get_db_session
from ..repositories.knowledge_document_repository import KnowledgeDocumentRepository
from ..schemas.admin import (
    AgentSettingsResponse,
    ConversationListResponse,
    LoginRequest,
    LoginResponse,
)
from ..schemas.agent_settings import AgentSettingsUpdate
from ..schemas.conversation_detail import ConversationDetail
from ..schemas.knowledge import KnowledgeDocumentGroup, KnowledgeIngestResult
from ..schemas.metrics import MetricsResponse
from ..security.admin_auth import _token_from_header, login, logout, require_admin
from ..services.admin_service import AdminService
from ..services.agent_settings_service import AgentSettingsService
from ..services.conversation_detail_service import ConversationDetailService
from ..services.document_ingestion_service import DocumentParseError, ingest
from ..services.metrics_service import MetricsService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=LoginResponse)
def admin_login(body: LoginRequest) -> LoginResponse:
    return LoginResponse(token=login(body.password))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def admin_logout(authorization: str | None = Header(default=None)) -> Response:
    logout(_token_from_header(authorization))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    dependencies=[Depends(require_admin)],
)
def admin_metrics(session: Session = Depends(get_db_session)) -> MetricsResponse:
    return MetricsService(session).build()


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    dependencies=[Depends(require_admin)],
)
def admin_conversations(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> ConversationListResponse:
    return AdminService(session).list_conversations(limit=limit, offset=offset)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    dependencies=[Depends(require_admin)],
)
def admin_conversation_detail(
    conversation_id: UUID,
    session: Session = Depends(get_db_session),
) -> ConversationDetail:
    detail = ConversationDetailService(session).build(conversation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return detail


@router.get(
    "/agent-settings",
    response_model=AgentSettingsResponse,
    dependencies=[Depends(require_admin)],
)
def get_agent_settings(session: Session = Depends(get_db_session)) -> AgentSettingsResponse:
    svc = AgentSettingsService(session)
    return AgentSettingsResponse(
        system_prompt=svc.effective_system_prompt(),
        is_custom=svc.is_custom(),
        knowledge_enabled=svc.get().knowledge_enabled,
    )


@router.put(
    "/agent-settings",
    response_model=AgentSettingsResponse,
    dependencies=[Depends(require_admin)],
)
def update_agent_settings(
    body: AgentSettingsUpdate, session: Session = Depends(get_db_session)
) -> AgentSettingsResponse:
    AgentSettingsService(session).repository.update(body.system_prompt, body.knowledge_enabled)
    return get_agent_settings(session)


@router.post(
    "/agent-settings/reset",
    response_model=AgentSettingsResponse,
    dependencies=[Depends(require_admin)],
)
def reset_agent_settings(session: Session = Depends(get_db_session)) -> AgentSettingsResponse:
    AgentSettingsService(session).repository.reset_prompt()
    return get_agent_settings(session)


@router.get(
    "/knowledge",
    response_model=list[KnowledgeDocumentGroup],
    dependencies=[Depends(require_admin)],
)
def list_knowledge(session: Session = Depends(get_db_session)) -> list[KnowledgeDocumentGroup]:
    return KnowledgeDocumentRepository(session).list_groups()


@router.post(
    "/knowledge",
    response_model=KnowledgeIngestResult,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
async def add_knowledge(
    session: Session = Depends(get_db_session),
    title: str = Form(...),
    category: str | None = Form(None),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
) -> KnowledgeIngestResult:
    try:
        if file is not None:
            data = await file.read()
            chunks, result = ingest(
                title=title,
                category=category,
                source=file.filename,
                file_bytes=data,
                filename=file.filename,
            )
        else:
            chunks, result = ingest(
                title=title,
                category=category,
                source="texto colado",
                pasted_text=text,
            )
    except DocumentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    KnowledgeDocumentRepository(session).insert_chunks(
        result.document_group_id, title, result.source, category, chunks
    )
    return result


@router.patch("/knowledge/{group_id}", dependencies=[Depends(require_admin)])
def set_knowledge_active(
    group_id: UUID, is_active: bool, session: Session = Depends(get_db_session)
) -> dict:
    n = KnowledgeDocumentRepository(session).set_active(group_id, is_active)
    if n == 0:
        raise HTTPException(status_code=404, detail="documento não encontrado")
    return {"updated": n}


@router.delete(
    "/knowledge/{group_id}",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
def delete_knowledge(group_id: UUID, session: Session = Depends(get_db_session)) -> Response:
    n = KnowledgeDocumentRepository(session).delete_group(group_id)
    if n == 0:
        raise HTTPException(status_code=404, detail="documento não encontrado")
    return Response(status_code=204)
