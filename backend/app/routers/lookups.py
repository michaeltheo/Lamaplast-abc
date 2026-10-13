from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.db import DbSession
from app.core.deps import get_current_user
from app.core.pagination import Pagination, paginate
from app.core.responses import ok
from app.models import (
    BSSG,
    Activity,
    BaseMaterial,
    CommercialPillar,
    CostCenter,
    GlobalDefault,
    ItemCodeRule,
    MachineCategory,
    ProductGroup,
    Scenario,
)
from app.schemas.lookups import (
    ActivityOut,
    BaseMaterialOut,
    BSSGOut,
    CommercialPillarOut,
    CostCenterOut,
    GlobalDefaultOut,
    ItemCodeRuleOut,
    MachineCategoryOut,
    ProductGroupOut,
    ScenarioOut,
)
from app.schemas.pagination import Page
from app.schemas.response import ApiResponse

router = APIRouter(prefix="/api/lookups", tags=["Lookups"], dependencies=[Depends(get_current_user)])


@router.get("/item-code-rules", response_model=ApiResponse[Page[ItemCodeRuleOut]])
def item_code_rules(p: Pagination, db: DbSession):
    return ok(paginate(db, select(ItemCodeRule).order_by(ItemCodeRule.Prefix), p))


@router.get("/base-materials", response_model=ApiResponse[Page[BaseMaterialOut]])
def base_materials(p: Pagination, db: DbSession, active_only: bool = True):
    query = select(BaseMaterial).order_by(BaseMaterial.Material_Code)
    if active_only:
        query = query.where(BaseMaterial.Is_Active)
    return ok(paginate(db, query, p))


@router.get("/bssg", response_model=ApiResponse[Page[BSSGOut]])
def bssg(p: Pagination, db: DbSession, active_only: bool = True):
    query = select(BSSG).order_by(BSSG.Sort_order, BSSG.BSSG_Code)
    if active_only:
        query = query.where(BSSG.Is_Active)
    return ok(paginate(db, query, p))


@router.get("/pillars", response_model=ApiResponse[Page[CommercialPillarOut]])
def pillars(p: Pagination, db: DbSession, bssg: str | None = None, active_only: bool = True):
    query = select(CommercialPillar).order_by(
        CommercialPillar.BSSG_Code, CommercialPillar.Sort_order, CommercialPillar.Pillar_Code)
    if bssg is not None:
        query = query.where(CommercialPillar.BSSG_Code == bssg)
    if active_only:
        query = query.where(CommercialPillar.Is_Active)
    return ok(paginate(db, query, p))


@router.get("/product-groups", response_model=ApiResponse[Page[ProductGroupOut]])
def product_groups(p: Pagination, db: DbSession, pillar: str | None = None, active_only: bool = True):
    query = select(ProductGroup).order_by(
        ProductGroup.Pillar_Code, ProductGroup.Sort_Order, ProductGroup.Group_Code)
    if pillar is not None:
        query = query.where(ProductGroup.Pillar_Code == pillar)
    if active_only:
        query = query.where(ProductGroup.Is_Active)
    return ok(paginate(db, query, p))


@router.get("/machine-categories", response_model=ApiResponse[Page[MachineCategoryOut]])
def machine_categories(p: Pagination, db: DbSession, group: str | None = None):
    query = select(MachineCategory).order_by(MachineCategory.Machine_Group.desc(), MachineCategory.Category_Code)
    if group is not None:
        query = query.where(MachineCategory.Machine_Group == group)
    return ok(paginate(db, query, p))


@router.get("/global-defaults", response_model=ApiResponse[Page[GlobalDefaultOut]])
def global_defaults(p: Pagination, db: DbSession):
    return ok(paginate(db, select(GlobalDefault).order_by(GlobalDefault.Parameter), p))


# --- δομή ABC (μόνο ανάγνωση· η διαχείριση σεναρίων έρχεται στη Φάση G) ---

@router.get("/cost-centers", response_model=ApiResponse[Page[CostCenterOut]])
def cost_centers(p: Pagination, db: DbSession, active_only: bool = True):
    query = select(CostCenter).order_by(CostCenter.CC_Code)
    if active_only:
        query = query.where(CostCenter.Is_Active)
    return ok(paginate(db, query, p))


@router.get("/activities", response_model=ApiResponse[Page[ActivityOut]])
def activities(p: Pagination, db: DbSession, cc_id: int | None = None, active_only: bool = True):
    query = select(Activity).order_by(Activity.Activity_Code)
    if cc_id is not None:
        query = query.where(Activity.CC_ID == cc_id)
    if active_only:
        query = query.where(Activity.Is_Active)
    return ok(paginate(db, query, p))


@router.get("/scenarios", response_model=ApiResponse[Page[ScenarioOut]])
def scenarios(p: Pagination, db: DbSession, open_only: bool = False):
    query = select(Scenario).order_by(Scenario.Period_Year.desc(), Scenario.Scenario_Name)
    if open_only:
        query = query.where(~Scenario.Is_Locked)
    return ok(paginate(db, query, p))
