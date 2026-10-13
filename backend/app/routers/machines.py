from typing import Annotated

from app.core.db import DbSession
from app.core.deps import get_current_user, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import User
from app.schemas.machines import MachineCreate, MachineOut, MachineUpdate
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse
from app.services import machines as service
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/api/machines", tags=["Μηχανές"], dependencies=[Depends(get_current_user)])

Editor = Annotated[User, Depends(require_module("MACHINES", edit=True))]


@router.get("", response_model=ApiResponse[Page[MachineOut]])
def list_machines(p: Pagination, db: DbSession, q: str | None = None, category: str | None = None,
                  cc_id: int | None = None, building_id: int | None = None, is_active: bool = True):
    query = service.machines_query(q=q, category=category, cc_id=cc_id, building_id=building_id,
                                   is_active=is_active)
    return ok(paginate(db, query, p))


@router.get("/{machine_id}", response_model=ApiResponse[MachineOut])
def get_machine(machine_id: int, db: DbSession):
    return ok(service.get_machine(db, machine_id))


@router.post("", response_model=ApiResponse[MachineOut], status_code=status.HTTP_201_CREATED)
def create_machine(body: MachineCreate, db: DbSession, user: Editor):
    machine = service.create_machine(db, body, user)
    db.commit()
    return ok(machine, status.HTTP_201_CREATED)


@router.patch("/{machine_id}", response_model=ApiResponse[MachineOut])
def update_machine(machine_id: int, body: MachineUpdate, db: DbSession, user: Editor):
    machine = service.update_machine(db, machine_id, body, user)
    db.commit()
    return ok(machine)


@router.post("/{machine_id}/deactivate", response_model=ApiResponse[MachineOut])
def deactivate_machine(machine_id: int, db: DbSession, user: Editor):
    machine = service.set_active(db, machine_id, False, user)
    db.commit()
    return ok(machine)


@router.post("/{machine_id}/activate", response_model=ApiResponse[MachineOut])
def activate_machine(machine_id: int, db: DbSession, user: Editor):
    machine = service.set_active(db, machine_id, True, user)
    db.commit()
    return ok(machine)
