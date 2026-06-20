from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db_session
from ..schemas.metrics import MetricsResponse
from ..services.metrics_service import MetricsService

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
def metrics(session: Session = Depends(get_db_session)) -> MetricsResponse:
    return MetricsService(session).build()
