from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.audit import snapshot
from app.models import Building, Machine, MachineCategory, User
from app.schemas.machines import MachineCreate, MachineUpdate

from . import common
from .errors import BusinessRuleError, ConflictError


def get_machine(db: Session, machine_id: int) -> Machine:
    return common.get_or_404(db, Machine, machine_id, "Η μηχανή δεν βρέθηκε")


def machines_query(*, q: str | None = None, category: str | None = None, cc_id: int | None = None,
                   building_id: int | None = None, is_active: bool | None = True) -> Select:
    query = select(Machine).order_by(Machine.Machine_Code)
    query = common.text_search(query, q, Machine.Machine_Code, Machine.Description)
    return common.where_equal(query, {Machine.Category_Code: category, Machine.CC_ID: cc_id,
                                      Machine.Building_ID: building_id, Machine.Is_Active: is_active})


def _validate(db: Session, values: dict, machine_id: int | None) -> ConflictError:
    """values = όλες οι τιμές που θα έχει η μηχανή μετά την αλλαγή."""
    code = values["Machine_Code"]
    conflict = ConflictError(f"Ο κωδικός μηχανής {code} υπάρχει ήδη")
    common.ensure_unique(db, Machine.Machine_ID, machine_id, conflict, Machine.Machine_Code == code)

    if db.get(MachineCategory, values["Category_Code"]) is None:
        raise BusinessRuleError(f"Η κατηγορία μηχανής {values['Category_Code']} δεν υπάρχει")
    common.check_cost_center(db, values["CC_ID"])
    if values["Building_ID"] is not None and db.get(Building, values["Building_ID"]) is None:
        raise BusinessRuleError(f"Το κτίριο με ID {values['Building_ID']} δεν υπάρχει")
    common.check_resource(db, values["Resource_ID"], "MACHINE")

    # Αλλιώς η αποσβέσιμη αξία (κτήση − υπολειμματική) θα έβγαινε αρνητική
    cost, residual = values["Acquisition_Cost_EUR"], values["Residual_Value_EUR"]
    if cost is not None and residual > cost:
        raise BusinessRuleError("Η υπολειμματική αξία δεν μπορεί να ξεπερνά το κόστος κτήσης")
    return conflict


def create_machine(db: Session, data: MachineCreate, user: User) -> Machine:
    values = data.model_dump()
    conflict = _validate(db, values, None)
    return common.insert(db, Machine(**values), user, conflict)


def update_machine(db: Session, machine_id: int, data: MachineUpdate, user: User) -> Machine:
    machine = get_machine(db, machine_id)
    changes = data.model_dump(exclude_unset=True)
    conflict = _validate(db, {**snapshot(machine), **changes}, machine.Machine_ID)
    return common.update(db, machine, changes, user, conflict)


def set_active(db: Session, machine_id: int, active: bool, user: User) -> Machine:
    return common.set_active(db, get_machine(db, machine_id), active, user)
