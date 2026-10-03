from app.core.config import settings
from app.core.db import get_db
from app.models import CostCenter
from app.schemas.health import HealthCheckResponse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api", tags=["System"])

@router.get("/health", response_model=HealthCheckResponse)
def health(db: Session = Depends(get_db)) -> HealthCheckResponse:
    try:
        db_name = db.execute(text("SELECT DB_NAME()")).scalar_one()
        cc_count = db.scalar(select(func.count()).select_from(CostCenter))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Η βάση δεν απαντάει: {exc.__class__.__name__}",
        ) from exc

    return HealthCheckResponse(status="ok", environment=settings.app_env, database=db_name, cost_centers=cc_count)