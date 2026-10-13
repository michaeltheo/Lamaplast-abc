from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.db import DbSession
from app.core.deps import get_current_user, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import User
from app.schemas.assembly_ops import (
    AssemblyOpCreate,
    AssemblyOpOut,
    AssemblyOpUpdate,
    OperationType,
)
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse
from app.services import assembly_ops as service

router = APIRouter(prefix="/api/assembly-ops", tags=["Συναρμολόγηση"], dependencies=[Depends(get_current_user)])

Editor = Annotated[User, Depends(require_module("MOULDS", edit=True))]


@router.get("", response_model=ApiResponse[Page[AssemblyOpOut]])
def list_ops(p: Pagination, db: DbSession, q: str | None = None, item_id: int | None = None,
             operation_type: OperationType | None = None, is_active: bool = True):
    query = service.ops_query(q=q, item_id=item_id, operation_type=operation_type, is_active=is_active)
    return ok(paginate(db, query, p))


@router.get("/{op_id}", response_model=ApiResponse[AssemblyOpOut])
def get_op(op_id: int, db: DbSession):
    return ok(service.get_op(db, op_id))


@router.post("", response_model=ApiResponse[AssemblyOpOut], status_code=status.HTTP_201_CREATED)
def create_op(body: AssemblyOpCreate, db: DbSession, user: Editor):
    op = service.create_op(db, body, user)
    db.commit()
    return ok(op, status.HTTP_201_CREATED)


@router.patch("/{op_id}", response_model=ApiResponse[AssemblyOpOut])
def update_op(op_id: int, body: AssemblyOpUpdate, db: DbSession, user: Editor):
    op = service.update_op(db, op_id, body, user)
    db.commit()
    return ok(op)


@router.post("/{op_id}/deactivate", response_model=ApiResponse[AssemblyOpOut])
def deactivate_op(op_id: int, db: DbSession, user: Editor):
    op = service.set_active(db, op_id, False, user)
    db.commit()
    return ok(op)


@router.post("/{op_id}/activate", response_model=ApiResponse[AssemblyOpOut])
def activate_op(op_id: int, db: DbSession, user: Editor):
    op = service.set_active(db, op_id, True, user)
    db.commit()
    return ok(op)
