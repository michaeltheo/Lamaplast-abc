from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.audit import log_change, snapshot
from app.models import (
    Activity,
    Building,
    LaborResource,
    Machine,
    Resource,
    ResourceActivity,
    User,
)
from app.schemas.resources import ActivityShareIn, ResourceCreate, ResourceUpdate

from . import common
from .errors import BusinessRuleError, ConflictError

# Το Share_Pct είναι Numeric(7, 6): η ανοχή είναι μία μονάδα στο τελευταίο δεκαδικό
SHARE_TOLERANCE = Decimal("0.000001")
_SHARE_FIELDS = ("Share_Pct", "Allocation_Basis", "Notes")


def get_resource(db: Session, resource_id: int) -> Resource:
    return common.get_or_404(db, Resource, resource_id, "Ο πόρος δεν βρέθηκε")


def resources_query(*, q: str | None = None, resource_type: str | None = None, cc_id: int | None = None,
                    is_active: bool | None = True) -> Select:
    query = select(Resource).order_by(Resource.Resource_Code)
    query = common.text_search(query, q, Resource.Resource_Code, Resource.Resource_Name)
    return common.where_equal(query, {Resource.Resource_Type: resource_type, Resource.CC_ID: cc_id,
                                      Resource.Is_Active: is_active})


def _validate(db: Session, values: dict, resource: Resource | None) -> ConflictError:
    code = values["Resource_Code"]
    conflict = ConflictError(f"Ο κωδικός πόρου {code} υπάρχει ήδη")
    common.ensure_unique(db, Resource.Resource_ID, resource.Resource_ID if resource else None, conflict,
                         Resource.Resource_Code == code)
    common.check_cost_center(db, values["CC_ID"])

    # Μια μηχανή δείχνει μόνο σε πόρο τύπου MACHINE κ.ο.κ.: ο τύπος δεν αλλάζει όσο κάτι δείχνει στον πόρο
    if resource is not None and values["Resource_Type"] != resource.Resource_Type:
        for model, label in ((Machine, "μηχανές"), (Building, "κτίρια"), (LaborResource, "εργαζόμενοι")):
            if db.scalar(select(func.count()).select_from(model).where(model.Resource_ID == resource.Resource_ID)):
                raise BusinessRuleError(f"Ο τύπος του πόρου {code} δεν αλλάζει: τον χρησιμοποιούν {label}")
    return conflict


def create_resource(db: Session, data: ResourceCreate, user: User) -> Resource:
    values = data.model_dump()
    conflict = _validate(db, values, None)
    return common.insert(db, Resource(**values), user, conflict)


def update_resource(db: Session, resource_id: int, data: ResourceUpdate, user: User) -> Resource:
    resource = get_resource(db, resource_id)
    changes = data.model_dump(exclude_unset=True)
    conflict = _validate(db, {**snapshot(resource), **changes}, resource)
    return common.update(db, resource, changes, user, conflict)


def set_active(db: Session, resource_id: int, active: bool, user: User) -> Resource:
    return common.set_active(db, get_resource(db, resource_id), active, user)


# --- ποσοστά ανά δραστηριότητα ---

def _shares(db: Session, resource_id: int, scenario_id: int) -> list[ResourceActivity]:
    return list(db.scalars(select(ResourceActivity)
                           .where(ResourceActivity.Resource_ID == resource_id,
                                  ResourceActivity.Scenario_ID == scenario_id)
                           .order_by(ResourceActivity.Activity_ID)))


def get_shares(db: Session, resource_id: int, scenario_id: int) -> list[ResourceActivity]:
    get_resource(db, resource_id)
    common.get_scenario(db, scenario_id)
    return _shares(db, resource_id, scenario_id)


def _share_values(share) -> dict:
    return {field: getattr(share, field) for field in _SHARE_FIELDS}


def replace_shares(db: Session, resource_id: int, scenario_id: int, shares: list[ActivityShareIn],
                   user: User) -> list[ResourceActivity]:
    """Αντικαθιστά ΟΛΑ τα ποσοστά του πόρου στο σενάριο. Άδεια λίστα = ο πόρος μένει χωρίς κατανομή."""
    resource = get_resource(db, resource_id)
    common.open_scenario(db, scenario_id)

    wanted = {s.Activity_ID: s for s in shares}
    if len(wanted) != len(shares):
        raise BusinessRuleError("Η ίδια δραστηριότητα δόθηκε δύο φορές")
    active = dict(db.execute(select(Activity.Activity_ID, Activity.Is_Active)
                             .where(Activity.Activity_ID.in_(wanted))).all())
    for activity_id in wanted:
        if activity_id not in active:
            raise BusinessRuleError(f"Η δραστηριότητα με ID {activity_id} δεν υπάρχει")
        if not active[activity_id]:
            raise BusinessRuleError(f"Η δραστηριότητα με ID {activity_id} είναι ανενεργή")

    total = sum((s.Share_Pct for s in shares), Decimal(0))
    if shares and not common.is_whole(total, SHARE_TOLERANCE):
        raise BusinessRuleError(f"Τα ποσοστά του πόρου {resource.Resource_Code} αθροίζουν "
                                f"{common.pct_text(total)} (πρέπει 100%)")

    current = {s.Activity_ID: s for s in _shares(db, resource_id, scenario_id)}
    before = {str(activity_id): _share_values(s) for activity_id, s in current.items()}
    for activity_id, share in current.items():
        if activity_id not in wanted:
            db.delete(share)
    for activity_id, new in wanted.items():
        share = current.get(activity_id)
        if share is None:
            db.add(ResourceActivity(Scenario_ID=scenario_id, Resource_ID=resource_id, **new.model_dump(),
                                    Created_By=user.Username))
        elif _share_values(share) != _share_values(new):
            for field in _SHARE_FIELDS:
                setattr(share, field, getattr(new, field))
            share.Updated_By = user.Username
    db.flush()

    after = {str(activity_id): _share_values(s) for activity_id, s in wanted.items()}
    log_change(db, user, ResourceActivity.__tablename__, f"Resource_ID={resource_id};Scenario_ID={scenario_id}",
               before, after)
    return _shares(db, resource_id, scenario_id)


def allocation_check(db: Session, scenario_id: int) -> list[dict]:
    """Οι ενεργοί πόροι που ΔΕΝ είναι έτοιμοι για υπολογισμό στο σενάριο: χωρίς ποσοστά ή με άθροισμα ≠ 100%.
    Άδεια λίστα = όλα εντάξει. Το καλεί ο engine πριν τρέξει."""
    common.get_scenario(db, scenario_id)
    totals = {resource_id: (total, count) for resource_id, total, count in db.execute(
        select(ResourceActivity.Resource_ID, func.sum(ResourceActivity.Share_Pct), func.count())
        .where(ResourceActivity.Scenario_ID == scenario_id).group_by(ResourceActivity.Resource_ID))}

    issues = []
    for resource in db.scalars(select(Resource).where(Resource.Is_Active).order_by(Resource.Resource_Code)):
        total, count = totals.get(resource.Resource_ID, (Decimal(0), 0))
        if count and common.is_whole(total, SHARE_TOLERANCE):
            continue
        message = f"Αθροίζει {common.pct_text(total)} (πρέπει 100%)" if count else "Δεν έχει ποσοστά"
        issues.append({"Resource_ID": resource.Resource_ID, "Resource_Code": resource.Resource_Code,
                       "Resource_Name": resource.Resource_Name, "Resource_Type": resource.Resource_Type,
                       "Activities": count, "Total_Share_Pct": total, "Message": message})
    return issues
