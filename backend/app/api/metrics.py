from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db_session
from ..schemas.metrics import MetricsResponse
from ..security.admin_auth import require_admin
from ..services.metrics_service import MetricsService

router = APIRouter(tags=["metrics"])


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    dependencies=[Depends(require_admin)],
)
def metrics(session: Session = Depends(get_db_session)) -> MetricsResponse:
    return MetricsService(session).build()
