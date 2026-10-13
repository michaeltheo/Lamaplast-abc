from typing import Annotated

from app.core.db import DbSession
from app.core.deps import get_current_user, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import User
from app.schemas.moulds import MouldCreate, MouldOut, MouldOwner, MouldType, MouldUpdate
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse
from app.services import moulds as service
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/api/moulds", tags=["Καλούπια"], dependencies=[Depends(get_current_user)])

Editor = Annotated[User, Depends(require_module("MOULDS", edit=True))]


@router.get("", response_model=ApiResponse[Page[MouldOut]])
def list_moulds(p: Pagination, db: DbSession, q: str | None = None, mould_owner: MouldOwner | None = None,
                mould_type: MouldType | None = None, customer_id: int | None = None, is_active: bool = True):
    query = service.moulds_query(q=q, mould_owner=mould_owner, mould_type=mould_type, customer_id=customer_id,
                                 is_active=is_active)
    return ok(paginate(db, query, p))


@router.get("/{mould_id}", response_model=ApiResponse[MouldOut])
def get_mould(mould_id: int, db: DbSession):
    return ok(service.get_mould(db, mould_id))


@router.post("", response_model=ApiResponse[MouldOut], status_code=status.HTTP_201_CREATED)
def create_mould(body: MouldCreate, db: DbSession, user: Editor):
    mould = service.create_mould(db, body, user)
    db.commit()
    return ok(mould, status.HTTP_201_CREATED)


@router.patch("/{mould_id}", response_model=ApiResponse[MouldOut])
def update_mould(mould_id: int, body: MouldUpdate, db: DbSession, user: Editor):
    mould = service.update_mould(db, mould_id, body, user)
    db.commit()
    return ok(mould)


@router.post("/{mould_id}/deactivate", response_model=ApiResponse[MouldOut])
def deactivate_mould(mould_id: int, db: DbSession, user: Editor):
    mould = service.set_active(db, mould_id, False, user)
    db.commit()
    return ok(mould)


@router.post("/{mould_id}/activate", response_model=ApiResponse[MouldOut])
def activate_mould(mould_id: int, db: DbSession, user: Editor):
    mould = service.set_active(db, mould_id, True, user)
    db.commit()
    return ok(mould)
