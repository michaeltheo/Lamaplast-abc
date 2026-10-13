from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.db import DbSession
from app.core.deps import CurrentUser, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import LaborResource, User
from app.schemas.labor import LaborCreate, LaborOut, LaborUpdate
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse
from app.services import labor as service

router = APIRouter(prefix="/api/labor", tags=["Εργαζόμενοι"])

Editor = Annotated[User, Depends(require_module("LABOR", edit=True))]


def _out(employee: LaborResource, user: User) -> LaborOut:
    out = LaborOut.model_validate(employee)
    return out if service.sees_names(user) else out.model_copy(update={"Employee_Name": None})


@router.get("", response_model=ApiResponse[Page[LaborOut]])
def list_labor(p: Pagination, db: DbSession, user: CurrentUser, q: str | None = None,
               labor_category: str | None = None, cc_id: int | None = None, is_active: bool = True):
    query = service.labor_query(q=q, search_names=service.sees_names(user), labor_category=labor_category,
                                cc_id=cc_id, is_active=is_active)
    page = paginate(db, query, p)
    return ok({**page, "items": [_out(employee, user) for employee in page["items"]]})


@router.get("/{employee_id}", response_model=ApiResponse[LaborOut])
def get_labor(employee_id: int, db: DbSession, user: CurrentUser):
    return ok(_out(service.get_labor(db, employee_id), user))


@router.post("", response_model=ApiResponse[LaborOut], status_code=status.HTTP_201_CREATED)
def create_labor(body: LaborCreate, db: DbSession, user: Editor):
    employee = service.create_labor(db, body, user)
    db.commit()
    return ok(employee, status.HTTP_201_CREATED)


@router.patch("/{employee_id}", response_model=ApiResponse[LaborOut])
def update_labor(employee_id: int, body: LaborUpdate, db: DbSession, user: Editor):
    employee = service.update_labor(db, employee_id, body, user)
    db.commit()
    return ok(employee)


@router.post("/{employee_id}/deactivate", response_model=ApiResponse[LaborOut])
def deactivate_labor(employee_id: int, db: DbSession, user: Editor):
    employee = service.set_active(db, employee_id, False, user)
    db.commit()
    return ok(employee)


@router.post("/{employee_id}/activate", response_model=ApiResponse[LaborOut])
def activate_labor(employee_id: int, db: DbSession, user: Editor):
    employee = service.set_active(db, employee_id, True, user)
    db.commit()
    return ok(employee)
