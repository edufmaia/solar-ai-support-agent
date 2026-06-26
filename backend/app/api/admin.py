from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..config.database import get_db_session
from ..schemas.admin import ConversationListResponse, LoginRequest, LoginResponse
from ..schemas.conversation_detail import ConversationDetail
from ..schemas.metrics import MetricsResponse
from ..security.admin_auth import login, logout, require_admin
from ..services.admin_service import AdminService
from ..services.conversation_detail_service import ConversationDetailService
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
    logout(authorization[len("Bearer ") :].strip())
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
