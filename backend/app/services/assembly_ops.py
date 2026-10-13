from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.audit import snapshot
from app.models import Activity, AssemblyOp, Item, User
from app.schemas.assembly_ops import AssemblyOpCreate, AssemblyOpUpdate

from . import common
from .errors import BusinessRuleError, ConflictError


def get_op(db: Session, op_id: int) -> AssemblyOp:
    return common.get_or_404(db, AssemblyOp, op_id, "Η εργασία συναρμολόγησης δεν βρέθηκε")


def ops_query(*, q: str | None = None, item_id: int | None = None, operation_type: str | None = None,
              is_active: bool | None = True) -> Select:
    query = select(AssemblyOp).order_by(AssemblyOp.AssemblyOp_Code)
    query = common.text_search(query, q, AssemblyOp.AssemblyOp_Code, AssemblyOp.Operation_Name)
    return common.where_equal(query, {AssemblyOp.Item_ID: item_id, AssemblyOp.Operation_Type: operation_type,
                                      AssemblyOp.Is_Active: is_active})


def _validate(db: Session, values: dict, op_id: int | None) -> ConflictError:
    code = values["AssemblyOp_Code"]
    conflict = ConflictError(f"Ο κωδικός εργασίας {code} υπάρχει ήδη")
    common.ensure_unique(db, AssemblyOp.AssemblyOp_ID, op_id, conflict, AssemblyOp.AssemblyOp_Code == code)
    if db.get(Item, values["Item_ID"]) is None:
        raise BusinessRuleError(f"Το είδος με ID {values['Item_ID']} δεν υπάρχει")
    activity_id = values["Activity_ID"]
    if activity_id is not None and db.get(Activity, activity_id) is None:
        raise BusinessRuleError(f"Η δραστηριότητα με ID {activity_id} δεν υπάρχει")
    return conflict


def create_op(db: Session, data: AssemblyOpCreate, user: User) -> AssemblyOp:
    values = data.model_dump()
    conflict = _validate(db, values, None)
    return common.insert(db, AssemblyOp(**values), user, conflict)


def update_op(db: Session, op_id: int, data: AssemblyOpUpdate, user: User) -> AssemblyOp:
    op = get_op(db, op_id)
    changes = data.model_dump(exclude_unset=True)
    conflict = _validate(db, {**snapshot(op), **changes}, op.AssemblyOp_ID)
    return common.update(db, op, changes, user, conflict)


def set_active(db: Session, op_id: int, active: bool, user: User) -> AssemblyOp:
    return common.set_active(db, get_op(db, op_id), active, user)
