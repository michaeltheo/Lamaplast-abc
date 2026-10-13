from typing import Annotated

from app.core.db import DbSession
from app.core.deps import get_current_user, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import User
from app.schemas.pagination import Page
from app.schemas.resources import (
    ActivityShareIn,
    ActivityShareOut,
    AllocationIssueOut,
    ResourceCreate,
    ResourceOut,
    ResourceType,
    ResourceUpdate,
)
from app.schemas.response import ApiResponse
from app.services import resources as service
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/api/resources", tags=["Πόροι"], dependencies=[Depends(get_current_user)])

Editor = Annotated[User, Depends(require_module("COST_STRUCTURE", edit=True))]


@router.get("", response_model=ApiResponse[Page[ResourceOut]])
def list_resources(p: Pagination, db: DbSession, q: str | None = None, resource_type: ResourceType | None = None,
                   cc_id: int | None = None, is_active: bool = True):
    query = service.resources_query(q=q, resource_type=resource_type, cc_id=cc_id, is_active=is_active)
    return ok(paginate(db, query, p))


# Πριν από το /{resource_id}: αλλιώς το "allocation-check" θα διαβαζόταν σαν resource_id
@router.get("/allocation-check", response_model=ApiResponse[list[AllocationIssueOut]])
def allocation_check(scenario_id: int, db: DbSession):
    return ok(service.allocation_check(db, scenario_id))


@router.get("/{resource_id}", response_model=ApiResponse[ResourceOut])
def get_resource(resource_id: int, db: DbSession):
    return ok(service.get_resource(db, resource_id))


@router.post("", response_model=ApiResponse[ResourceOut], status_code=status.HTTP_201_CREATED)
def create_resource(body: ResourceCreate, db: DbSession, user: Editor):
    resource = service.create_resource(db, body, user)
    db.commit()
    return ok(resource, status.HTTP_201_CREATED)


@router.patch("/{resource_id}", response_model=ApiResponse[ResourceOut])
def update_resource(resource_id: int, body: ResourceUpdate, db: DbSession, user: Editor):
    resource = service.update_resource(db, resource_id, body, user)
    db.commit()
    return ok(resource)


@router.post("/{resource_id}/deactivate", response_model=ApiResponse[ResourceOut])
def deactivate_resource(resource_id: int, db: DbSession, user: Editor):
    resource = service.set_active(db, resource_id, False, user)
    db.commit()
    return ok(resource)


@router.post("/{resource_id}/activate", response_model=ApiResponse[ResourceOut])
def activate_resource(resource_id: int, db: DbSession, user: Editor):
    resource = service.set_active(db, resource_id, True, user)
    db.commit()
    return ok(resource)


@router.get("/{resource_id}/activities", response_model=ApiResponse[list[ActivityShareOut]])
def get_activity_shares(resource_id: int, scenario_id: int, db: DbSession):
    return ok(service.get_shares(db, resource_id, scenario_id))


@router.put("/{resource_id}/activities", response_model=ApiResponse[list[ActivityShareOut]])
def replace_activity_shares(resource_id: int, scenario_id: int, body: list[ActivityShareIn], db: DbSession,
                            user: Editor):
    shares = service.replace_shares(db, resource_id, scenario_id, body, user)
    db.commit()
    return ok(shares)
