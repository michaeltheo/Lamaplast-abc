from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, text

from app.core.config import settings
from app.core.db import DbSession
from app.core.responses import ok
from app.models import CostCenter
from app.schemas.health import HealthCheckResponse
from app.schemas.response import ApiResponse

router = APIRouter(prefix="/api", tags=["System"])

@router.get("/health", response_model=ApiResponse[HealthCheckResponse])
def health(db: DbSession):
    try:
        db_name = db.execute(text("SELECT DB_NAME()")).scalar_one()
        cc_count = db.scalar(select(func.count()).select_from(CostCenter))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Η βάση δεν απαντάει: {exc.__class__.__name__}",
        ) from exc

    return ok(HealthCheckResponse(status="ok", environment=settings.app_env, database=db_name, cost_centers=cc_count))