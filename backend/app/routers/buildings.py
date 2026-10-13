from typing import Annotated

from app.core.db import DbSession
from app.core.deps import get_current_user, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import User
from app.schemas.buildings import BuildingCreate, BuildingOut, BuildingUpdate
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse
from app.services import buildings as service
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/api/buildings", tags=["Κτίρια"], dependencies=[Depends(get_current_user)])

Editor = Annotated[User, Depends(require_module("BUILDINGS", edit=True))]


@router.get("", response_model=ApiResponse[Page[BuildingOut]])
def list_buildings(p: Pagination, db: DbSession, q: str | None = None, cc_id: int | None = None,
                   is_active: bool = True):
    return ok(paginate(db, service.buildings_query(q=q, cc_id=cc_id, is_active=is_active), p))


@router.get("/{building_id}", response_model=ApiResponse[BuildingOut])
def get_building(building_id: int, db: DbSession):
    return ok(service.get_building(db, building_id))


@router.post("", response_model=ApiResponse[BuildingOut], status_code=status.HTTP_201_CREATED)
def create_building(body: BuildingCreate, db: DbSession, user: Editor):
    building = service.create_building(db, body, user)
    db.commit()
    return ok(building, status.HTTP_201_CREATED)


@router.patch("/{building_id}", response_model=ApiResponse[BuildingOut])
def update_building(building_id: int, body: BuildingUpdate, db: DbSession, user: Editor):
    building = service.update_building(db, building_id, body, user)
    db.commit()
    return ok(building)


@router.post("/{building_id}/deactivate", response_model=ApiResponse[BuildingOut])
def deactivate_building(building_id: int, db: DbSession, user: Editor):
    building = service.set_active(db, building_id, False, user)
    db.commit()
    return ok(building)


@router.post("/{building_id}/activate", response_model=ApiResponse[BuildingOut])
def activate_building(building_id: int, db: DbSession, user: Editor):
    building = service.set_active(db, building_id, True, user)
    db.commit()
    return ok(building)
