from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..config.database import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def health_db(session: Session = Depends(get_db_session)) -> dict[str, str]:
    try:
        result = session.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    if result != 1:
        raise HTTPException(status_code=503, detail="database unavailable")

    return {"status": "ok", "database": "connected"}
