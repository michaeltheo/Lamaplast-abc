from datetime import datetime
from typing import Annotated

from app.core.db import DbSession
from app.core.deps import require_role
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import AuditLog
from app.schemas.audit import AuditLogOut
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

router = APIRouter(prefix="/api/audit", tags=["Audit"], dependencies=[Depends(require_role("ADMIN"))])


@router.get("", response_model=ApiResponse[Page[AuditLogOut]])
def audit_log(
    p: Pagination,
    db: DbSession,
    table: str | None = None,
    user: str | None = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
):
    query = select(AuditLog).order_by(AuditLog.At.desc(), AuditLog.Audit_ID.desc())
    if table is not None:
        query = query.where(AuditLog.Table_Name == table)
    if user is not None:
        query = query.where(AuditLog.Username == user)
    if from_ is not None:
        query = query.where(AuditLog.At >= from_)
    if to is not None:
        query = query.where(AuditLog.At <= to)
    return ok(paginate(db, query, p))
