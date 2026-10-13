from typing import Annotated

from app.core.db import DbSession
from app.core.deps import get_current_user, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import User
from app.schemas.mould_runs import MouldRunIn, MouldRunOut
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse
from app.services import mould_runs as service
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/api/mould-runs", tags=["Mould runs"], dependencies=[Depends(get_current_user)])

Editor = Annotated[User, Depends(require_module("MOULDS", edit=True))]


@router.get("", response_model=ApiResponse[Page[MouldRunOut]])
def list_runs(p: Pagination, db: DbSession, q: str | None = None, item_id: int | None = None,
              mould_id: int | None = None, machine_category: str | None = None, is_active: bool = True):
    query = service.runs_query(q=q, item_id=item_id, mould_id=mould_id, machine_category=machine_category,
                               is_active=is_active)
    return ok(paginate(db, query, p))


@router.get("/{run_id}", response_model=ApiResponse[MouldRunOut])
def get_run(run_id: int, db: DbSession):
    return ok(service.get_run(db, run_id))


@router.post("", response_model=ApiResponse[MouldRunOut], status_code=status.HTTP_201_CREATED)
def create_run(body: MouldRunIn, db: DbSession, user: Editor):
    run = service.create_run(db, body, user)
    db.commit()
    return ok(run, status.HTTP_201_CREATED)


@router.put("/{run_id}", response_model=ApiResponse[MouldRunOut])
def replace_run(run_id: int, body: MouldRunIn, db: DbSession, user: Editor):
    run = service.replace_run(db, run_id, body, user)
    db.commit()
    return ok(run)


@router.post("/{run_id}/deactivate", response_model=ApiResponse[MouldRunOut])
def deactivate_run(run_id: int, db: DbSession, user: Editor):
    run = service.set_active(db, run_id, False, user)
    db.commit()
    return ok(run)


@router.post("/{run_id}/activate", response_model=ApiResponse[MouldRunOut])
def activate_run(run_id: int, db: DbSession, user: Editor):
    run = service.set_active(db, run_id, True, user)
    db.commit()
    return ok(run)
