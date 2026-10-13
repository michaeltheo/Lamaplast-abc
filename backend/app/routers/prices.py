"""Τιμές αγοράς, τιμές πώλησης και ετήσιοι όγκοι: τρεις routers, όλοι στην ενότητα PRICES.
Δεν έχουν activate/deactivate: μια τιμή «κλείνει» με το Valid_To της."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.db import DbSession
from app.core.deps import get_current_user, require_module
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import User
from app.schemas.pagination import Page
from app.schemas.prices import (
    ItemVolumeIn,
    ItemVolumeOut,
    PriceCreate,
    PriceOut,
    PriceUpdate,
    SalesPriceCreate,
    SalesPriceOut,
    SalesPriceUpdate,
)
from app.schemas.response import ApiResponse
from app.services import item_volumes
from app.services import prices as service

_logged_in = [Depends(get_current_user)]
prices_router = APIRouter(prefix="/api/prices", tags=["Τιμές αγοράς"], dependencies=_logged_in)
sales_router = APIRouter(prefix="/api/sales-prices", tags=["Τιμές πώλησης"], dependencies=_logged_in)
volumes_router = APIRouter(prefix="/api/item-volumes", tags=["Όγκοι ειδών"], dependencies=_logged_in)

Editor = Annotated[User, Depends(require_module("PRICES", edit=True))]


# --- τιμές αγοράς ---

@prices_router.get("", response_model=ApiResponse[Page[PriceOut]])
def list_prices(p: Pagination, db: DbSession, item_id: int | None = None, scenario_id: int | None = None,
                on: date | None = None):
    return ok(paginate(db, service.prices_query(item_id=item_id, scenario_id=scenario_id, on=on), p))


# Πριν από το /{price_id}: αλλιώς το "current" θα διαβαζόταν σαν price_id
@prices_router.get("/current", response_model=ApiResponse[PriceOut])
def current_price(item_id: int, scenario_id: int, db: DbSession, on: date | None = None):
    return ok(service.current_price(db, item_id, scenario_id, on or date.today()))


@prices_router.get("/{price_id}", response_model=ApiResponse[PriceOut])
def get_price(price_id: int, db: DbSession):
    return ok(service.get_price(db, price_id))


@prices_router.post("", response_model=ApiResponse[PriceOut], status_code=status.HTTP_201_CREATED)
def create_price(body: PriceCreate, db: DbSession, user: Editor):
    price = service.create_price(db, body, user)
    db.commit()
    return ok(price, status.HTTP_201_CREATED)


@prices_router.patch("/{price_id}", response_model=ApiResponse[PriceOut])
def update_price(price_id: int, body: PriceUpdate, db: DbSession, user: Editor):
    price = service.update_price(db, price_id, body, user)
    db.commit()
    return ok(price)


# --- τιμές πώλησης ---

@sales_router.get("", response_model=ApiResponse[Page[SalesPriceOut]])
def list_sales_prices(p: Pagination, db: DbSession, item_id: int | None = None, scenario_id: int | None = None,
                      customer_id: int | None = None, on: date | None = None):
    query = service.sales_prices_query(item_id=item_id, scenario_id=scenario_id, customer_id=customer_id, on=on)
    return ok(paginate(db, query, p))


@sales_router.get("/current", response_model=ApiResponse[SalesPriceOut])
def current_sales_price(item_id: int, scenario_id: int, db: DbSession, customer_id: int | None = None,
                        on: date | None = None):
    return ok(service.current_sales_price(db, item_id, scenario_id, customer_id, on or date.today()))


@sales_router.get("/{sales_price_id}", response_model=ApiResponse[SalesPriceOut])
def get_sales_price(sales_price_id: int, db: DbSession):
    return ok(service.get_sales_price(db, sales_price_id))


@sales_router.post("", response_model=ApiResponse[SalesPriceOut], status_code=status.HTTP_201_CREATED)
def create_sales_price(body: SalesPriceCreate, db: DbSession, user: Editor):
    price = service.create_sales_price(db, body, user)
    db.commit()
    return ok(price, status.HTTP_201_CREATED)


@sales_router.patch("/{sales_price_id}", response_model=ApiResponse[SalesPriceOut])
def update_sales_price(sales_price_id: int, body: SalesPriceUpdate, db: DbSession, user: Editor):
    price = service.update_sales_price(db, sales_price_id, body, user)
    db.commit()
    return ok(price)


# --- ετήσιοι όγκοι ---

@volumes_router.get("", response_model=ApiResponse[Page[ItemVolumeOut]])
def list_volumes(scenario_id: int, p: Pagination, db: DbSession, item_id: int | None = None):
    return ok(paginate(db, item_volumes.volumes_query(db, scenario_id, item_id=item_id), p))


@volumes_router.put("", response_model=ApiResponse[list[ItemVolumeOut]])
def upsert_volumes(scenario_id: int, body: list[ItemVolumeIn], db: DbSession, user: Editor):
    volumes = item_volumes.upsert_volumes(db, scenario_id, body, user)
    db.commit()
    return ok(volumes)
