from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.audit import snapshot
from app.models import LaborResource, User
from app.schemas.labor import LaborCreate, LaborUpdate

from . import common
from .errors import ConflictError


def sees_names(user: User) -> bool:
    """GDPR: τα ονόματα των εργαζομένων τα βλέπουν μόνο ADMIN και EXPERT."""
    return user.Role in ("ADMIN", "EXPERT")


def get_labor(db: Session, employee_id: int) -> LaborResource:
    return common.get_or_404(db, LaborResource, employee_id, "Ο εργαζόμενος δεν βρέθηκε")


def labor_query(*, q: str | None = None, search_names: bool = False, labor_category: str | None = None,
                cc_id: int | None = None, is_active: bool | None = True) -> Select:
    query = select(LaborResource).order_by(LaborResource.Employee_Code)
    # Χωρίς search_names το q δεν ψάχνει στο όνομα: αλλιώς ο USER θα το μάντευε δοκιμάζοντας
    columns = [LaborResource.Employee_Code, LaborResource.Labor_Category]
    if search_names:
        columns.append(LaborResource.Employee_Name)
    query = common.text_search(query, q, *columns)
    return common.where_equal(query, {LaborResource.Labor_Category: labor_category, LaborResource.CC_ID: cc_id,
                                      LaborResource.Is_Active: is_active})


def _validate(db: Session, values: dict, employee_id: int | None) -> ConflictError:
    """values = όλες οι τιμές που θα έχει ο εργαζόμενος μετά την αλλαγή."""
    code = values["Employee_Code"]
    conflict = ConflictError(f"Ο κωδικός εργαζομένου {code} υπάρχει ήδη")
    common.ensure_unique(db, LaborResource.Employee_ID, employee_id, conflict, LaborResource.Employee_Code == code)
    common.check_cost_center(db, values["CC_ID"])
    common.check_resource(db, values["Resource_ID"], "LABOR")
    return conflict


def create_labor(db: Session, data: LaborCreate, user: User) -> LaborResource:
    values = data.model_dump()
    conflict = _validate(db, values, None)
    return common.insert(db, LaborResource(**values), user, conflict)


def update_labor(db: Session, employee_id: int, data: LaborUpdate, user: User) -> LaborResource:
    employee = get_labor(db, employee_id)
    changes = data.model_dump(exclude_unset=True)
    conflict = _validate(db, {**snapshot(employee), **changes}, employee.Employee_ID)
    return common.update(db, employee, changes, user, conflict)


def set_active(db: Session, employee_id: int, active: bool, user: User) -> LaborResource:
    return common.set_active(db, get_labor(db, employee_id), active, user)
