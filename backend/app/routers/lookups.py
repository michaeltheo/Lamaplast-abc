from app.core.db import get_db
from app.core.pagination import Pagination, paginate
from app.models import (
    BSSG,
    BaseMaterial,
    CommercialPillar,
    GlobalDefault,
    ItemCodeRule,
    MachineCategory,
    ProductGroup,
)
from app.schemas.lookups import (
    BaseMaterialOut,
    BSSGOut,
    CommercialPillarOut,
    GlobalDefaultOut,
    ItemCodeRuleOut,
    MachineCategoryOut,
    ProductGroupOut,
)
from app.schemas.pagination import Page
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/lookups", tags=["Lookups"])


@router.get("/item-code-rules", response_model=Page[ItemCodeRuleOut])
def item_code_rules(p: Pagination, db: Session = Depends(get_db)):
    return paginate(db, select(ItemCodeRule).order_by(ItemCodeRule.Prefix), p)


@router.get("/base-materials", response_model=Page[BaseMaterialOut])
def base_materials(p: Pagination, active_only: bool = True, db: Session = Depends(get_db)):
    query = select(BaseMaterial).order_by(BaseMaterial.Material_Code)
    if active_only:
        query = query.where(BaseMaterial.Is_Active)
    return paginate(db, query, p)


@router.get("/bssg", response_model=Page[BSSGOut])
def bssg(p: Pagination, active_only: bool = True, db: Session = Depends(get_db)):
    query = select(BSSG).order_by(BSSG.Sort_order, BSSG.BSSG_Code)
    if active_only:
        query = query.where(BSSG.Is_Active)
    return paginate(db, query, p)


@router.get("/pillars", response_model=Page[CommercialPillarOut])
def pillars(p: Pagination, bssg: str | None = None, active_only: bool = True, db: Session = Depends(get_db)):
    query = select(CommercialPillar).order_by(
        CommercialPillar.BSSG_Code, CommercialPillar.Sort_order, CommercialPillar.Pillar_Code)
    if bssg is not None:
        query = query.where(CommercialPillar.BSSG_Code == bssg)
    if active_only:
        query = query.where(CommercialPillar.Is_Active)
    return paginate(db, query, p)


@router.get("/product-groups", response_model=Page[ProductGroupOut])
def product_groups(p: Pagination, pillar: str | None = None, active_only: bool = True, db: Session = Depends(get_db)):
    query = select(ProductGroup).order_by(
        ProductGroup.Pillar_Code, ProductGroup.Sort_Order, ProductGroup.Group_Code)
    if pillar is not None:
        query = query.where(ProductGroup.Pillar_Code == pillar)
    if active_only:
        query = query.where(ProductGroup.Is_Active)
    return paginate(db, query, p)


@router.get("/machine-categories", response_model=Page[MachineCategoryOut])
def machine_categories(p: Pagination, group: str | None = None, db: Session = Depends(get_db)):
    query = select(MachineCategory).order_by(MachineCategory.Machine_Group.desc(), MachineCategory.Category_Code)
    if group is not None:
        query = query.where(MachineCategory.Machine_Group == group)
    return paginate(db, query, p)


@router.get("/global-defaults", response_model=Page[GlobalDefaultOut])
def global_defaults(p: Pagination, db: Session = Depends(get_db)):
    return paginate(db, select(GlobalDefault).order_by(GlobalDefault.Parameter), p)
