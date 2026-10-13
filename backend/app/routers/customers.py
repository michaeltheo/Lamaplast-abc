from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.db import DbSession
from app.core.deps import get_current_user, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import User
from app.schemas.customers import CustomerCreate, CustomerOut, CustomerUpdate
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse
from app.services import customers as service

# Οι πελάτες ανήκουν στην ενότητα ITEMS: όποιος γράφει είδη γράφει και πελάτες.
router = APIRouter(prefix="/api/customers", tags=["Πελάτες"], dependencies=[Depends(get_current_user)])

Editor = Annotated[User, Depends(require_module("ITEMS", edit=True))]


@router.get("", response_model=ApiResponse[Page[CustomerOut]])
def list_customers(p: Pagination, db: DbSession, q: str | None = None, is_internal: bool | None = None,
                   is_active: bool = True):
    return ok(paginate(db, service.customers_query(q=q, is_internal=is_internal, is_active=is_active), p))


@router.get("/{customer_id}", response_model=ApiResponse[CustomerOut])
def get_customer(customer_id: int, db: DbSession):
    return ok(service.get_customer(db, customer_id))


@router.post("", response_model=ApiResponse[CustomerOut], status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, db: DbSession, user: Editor):
    customer = service.create_customer(db, body, user)
    db.commit()
    return ok(customer, status.HTTP_201_CREATED)


@router.patch("/{customer_id}", response_model=ApiResponse[CustomerOut])
def update_customer(customer_id: int, body: CustomerUpdate, db: DbSession, user: Editor):
    customer = service.update_customer(db, customer_id, body, user)
    db.commit()
    return ok(customer)


@router.post("/{customer_id}/deactivate", response_model=ApiResponse[CustomerOut])
def deactivate_customer(customer_id: int, db: DbSession, user: Editor):
    customer = service.set_active(db, customer_id, False, user)
    db.commit()
    return ok(customer)


@router.post("/{customer_id}/activate", response_model=ApiResponse[CustomerOut])
def activate_customer(customer_id: int, db: DbSession, user: Editor):
    customer = service.set_active(db, customer_id, True, user)
    db.commit()
    return ok(customer)
