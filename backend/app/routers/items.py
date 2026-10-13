from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.db import DbSession
from app.core.deps import get_current_user, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import User
from app.schemas.items import (
    ItemCreate,
    ItemListOut,
    ItemOut,
    ItemUpdate,
    LogisticsUnitIn,
)
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse
from app.services import items as service

# Ανάγνωση: κάθε συνδεδεμένος χρήστης. Εγγραφή: ADMIN ή EXPERT με Can_Edit στην ενότητα ITEMS.
router = APIRouter(prefix="/api/items", tags=["Είδη"], dependencies=[Depends(get_current_user)])

Editor = Annotated[User, Depends(require_module("ITEMS", edit=True))]


@router.get("", response_model=ApiResponse[Page[ItemListOut]])
def list_items(
    p: Pagination,
    db: DbSession,
    q: str | None = None,
    prefix: str | None = None,
    group_code: str | None = None,
    bssg_code: str | None = None,
    customer_id: int | None = None,
    is_active: bool = True,
    is_produced: bool | None = None,
    is_purchased: bool | None = None,
):
    query = service.items_query(q=q, prefix=prefix, group_code=group_code, bssg_code=bssg_code,
                                customer_id=customer_id, is_active=is_active,
                                is_produced=is_produced, is_purchased=is_purchased)
    return ok(paginate(db, query, p))


@router.get("/{item_id}", response_model=ApiResponse[ItemOut])
def get_item(item_id: int, db: DbSession):
    return ok(service.get_item(db, item_id))


@router.post("", response_model=ApiResponse[ItemOut], status_code=status.HTTP_201_CREATED)
def create_item(body: ItemCreate, db: DbSession, user: Editor):
    item = service.create_item(db, body, user)
    db.commit()
    return ok(item, status.HTTP_201_CREATED)


@router.patch("/{item_id}", response_model=ApiResponse[ItemOut])
def update_item(item_id: int, body: ItemUpdate, db: DbSession, user: Editor):
    item = service.update_item(db, item_id, body, user)
    db.commit()
    return ok(item)


@router.post("/{item_id}/deactivate", response_model=ApiResponse[ItemOut])
def deactivate_item(item_id: int, db: DbSession, user: Editor):
    item = service.set_active(db, item_id, False, user)
    db.commit()
    return ok(item)


@router.post("/{item_id}/activate", response_model=ApiResponse[ItemOut])
def activate_item(item_id: int, db: DbSession, user: Editor):
    item = service.set_active(db, item_id, True, user)
    db.commit()
    return ok(item)


@router.put("/{item_id}/logistics-units", response_model=ApiResponse[ItemOut])
def replace_logistics_units(item_id: int, body: list[LogisticsUnitIn], db: DbSession, user: Editor):
    item = service.replace_logistics_units(db, item_id, body, user)
    db.commit()
    return ok(item)
