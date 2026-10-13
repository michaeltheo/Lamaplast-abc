from decimal import Decimal

from app.core.audit import log_change, snapshot
from app.models import (
    MachineCategory,
    Mould,
    MouldRun,
    MouldRunMaterial,
    MouldRunOutput,
    User,
)
from app.schemas.mould_runs import MouldRunIn, MouldRunMaterialIn, MouldRunOutputIn
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from . import common
from .errors import BusinessRuleError, ConflictError, NotFoundError

# Ανοχή = μία μονάδα στο τελευταίο δεκαδικό της στήλης: Mix_Pct Numeric(7, 5), Cost_Share_Pct Numeric(7, 6)
MIX_TOLERANCE = Decimal("0.00001")
COST_SHARE_TOLERANCE = Decimal("0.000001")
_MATERIAL_ITEM_TYPES = ("RAW_MAT", "AUXILIARY")

# selectinload: outputs και materials έρχονται με δύο επιπλέον queries για ΟΛΑ τα runs της σελίδας, όχι δύο ανά run
_WITH_CHILDREN = (selectinload(MouldRun.outputs), selectinload(MouldRun.materials))


def get_run(db: Session, run_id: int) -> MouldRun:
    run = db.scalar(select(MouldRun).where(MouldRun.MouldRun_ID == run_id).options(*_WITH_CHILDREN))
    if run is None:
        raise NotFoundError("Το mould run δεν βρέθηκε")
    return run


def runs_query(*, q: str | None = None, item_id: int | None = None, mould_id: int | None = None,
               machine_category: str | None = None, is_active: bool | None = True) -> Select:
    query = select(MouldRun).options(*_WITH_CHILDREN).order_by(MouldRun.MouldRun_Code)
    query = common.text_search(query, q, MouldRun.MouldRun_Code)
    if item_id is not None:  # όλα τα runs που βγάζουν αυτό το είδος (το χρειάζεται το BOM)
        query = query.where(MouldRun.outputs.any(MouldRunOutput.Item_ID == item_id))
    return common.where_equal(query, {MouldRun.Mould_ID: mould_id, MouldRun.Machine_Category: machine_category,
                                      MouldRun.Is_Active: is_active})


# --- κανόνες ---

def _check_outputs(db: Session, outputs: list[MouldRunOutputIn], mould: Mould) -> None:
    item_ids = [o.Item_ID for o in outputs]
    if len(set(item_ids)) != len(item_ids):
        raise BusinessRuleError("Το ίδιο είδος δόθηκε δύο φορές στα outputs")
    known = common.item_types(db, item_ids)
    for item_id in item_ids:
        if item_id not in known:
            raise BusinessRuleError(f"Το είδος εξόδου με ID {item_id} δεν υπάρχει")

    # Cost_Share_Pct: όλα κενά (το κόστος μοιράζεται κατά βάρος) ή όλα συμπληρωμένα με άθροισμα 100%
    shares = [o.Cost_Share_Pct for o in outputs if o.Cost_Share_Pct is not None]
    if shares and len(shares) != len(outputs):
        raise BusinessRuleError("Τα Cost_Share_Pct συμπληρώνονται είτε σε όλα τα outputs είτε σε κανένα")
    if shares and not common.is_whole(sum(shares, Decimal(0)), COST_SHARE_TOLERANCE):
        raise BusinessRuleError(f"Τα Cost_Share_Pct αθροίζουν {common.pct_text(sum(shares, Decimal(0)))} "
                                f"(πρέπει 100%)")

    pieces = sum(o.Pieces_Per_Cycle for o in outputs)
    if mould.Mould_Type == "SINGLE" and (len(outputs) != 1 or pieces != 1):
        raise BusinessRuleError("Καλούπι SINGLE βγάζει ακριβώς ένα είδος με Pieces_Per_Cycle = 1")
    if mould.Mould_Type == "MULTI_CAVITY" and len(outputs) != 1:
        raise BusinessRuleError("Καλούπι MULTI_CAVITY βγάζει ένα μόνο είδος (για πολλά είδη: FAMILY)")
    if pieces > mould.Cavities:
        raise BusinessRuleError(f"Τα τεμάχια ανά κύκλο ({pieces}) ξεπερνούν τις κοιλότητες "
                                f"του καλουπιού ({mould.Cavities})")


def _check_materials(db: Session, materials: list[MouldRunMaterialIn]) -> None:
    item_ids = [m.Material_Item_ID for m in materials]
    if len(set(item_ids)) != len(item_ids):
        raise BusinessRuleError("Το ίδιο υλικό δόθηκε δύο φορές")
    known = common.item_types(db, item_ids)
    for item_id in item_ids:
        if item_id not in known:
            raise BusinessRuleError(f"Το υλικό με ID {item_id} δεν υπάρχει")
        code, item_type, purchased = known[item_id]
        if not purchased and item_type not in _MATERIAL_ITEM_TYPES:
            raise BusinessRuleError(f"Το είδος {code} δεν είναι πρώτη ύλη ούτε αγοραζόμενο")

    total = sum((m.Mix_Pct for m in materials), Decimal(0))
    if not common.is_whole(total, MIX_TOLERANCE):
        raise BusinessRuleError(f"Τα Mix_Pct αθροίζουν {common.pct_text(total)} (πρέπει 100%)")


def _validate(db: Session, data: MouldRunIn, run_id: int | None) -> ConflictError:
    common.ensure_unique(db, MouldRun.MouldRun_ID, run_id,
                         ConflictError(f"Ο κωδικός {data.MouldRun_Code} υπάρχει ήδη"),
                         MouldRun.MouldRun_Code == data.MouldRun_Code)
    mould = db.get(Mould, data.Mould_ID)
    if mould is None:
        raise BusinessRuleError(f"Το καλούπι με ID {data.Mould_ID} δεν υπάρχει")
    if db.get(MachineCategory, data.Machine_Category) is None:
        raise BusinessRuleError(f"Η κατηγορία μηχανής {data.Machine_Category} δεν υπάρχει")
    # Ένα run ανά καλούπι και κατηγορία μηχανής: το ίδιο καλούπι τρέχει αλλιώς σε μεγαλύτερη πρέσα
    common.ensure_unique(db, MouldRun.MouldRun_ID, run_id,
                         ConflictError(f"Το καλούπι {mould.Mould_Code} έχει ήδη run "
                                       f"στην κατηγορία {data.Machine_Category}"),
                         MouldRun.Mould_ID == data.Mould_ID, MouldRun.Machine_Category == data.Machine_Category)
    _check_outputs(db, data.outputs, mould)
    _check_materials(db, data.materials)
    return ConflictError("Υπάρχει ήδη run με αυτόν τον κωδικό ή για αυτό το καλούπι και κατηγορία μηχανής")


# --- εγγραφές (το commit το κάνει ο καλών): run + outputs + materials σε ένα transaction ---

def _child(row, key: str) -> dict:
    return {field: value for field, value in snapshot(row).items() if field not in ("MouldRun_ID", key)}


def _snapshot(run: MouldRun) -> dict:
    """Το run μαζί με τα παιδιά του, ώστε μία γραμμή audit να δείχνει όλη την αλλαγή."""
    return {**snapshot(run),
            "outputs": {str(o.Item_ID): _child(o, "Item_ID") for o in run.outputs},
            "materials": {str(m.Material_Item_ID): _child(m, "Material_Item_ID") for m in run.materials}}


def _sync(current: list, incoming: list, model, key: str, user: User) -> list:
    """Η νέα λίστα παιδιών: όσα υπάρχουν ήδη ενημερώνονται, τα καινούρια προστίθενται,
    και όσα λείπουν σβήνονται από το delete-orphan της σχέσης."""
    by_key = {getattr(row, key): row for row in current}
    result = []
    for new in incoming:
        values = new.model_dump()
        row = by_key.get(values[key])
        if row is None:
            row = model(**values, Created_By=user.Username)
        elif any(getattr(row, field) != value for field, value in values.items()):
            for field, value in values.items():
                setattr(row, field, value)
            row.Updated_By = user.Username
        result.append(row)
    return result


def _apply(run: MouldRun, data: MouldRunIn, user: User) -> None:
    for field, value in data.model_dump(exclude={"outputs", "materials"}).items():
        setattr(run, field, value)
    run.outputs = _sync(run.outputs, data.outputs, MouldRunOutput, "Item_ID", user)
    run.materials = _sync(run.materials, data.materials, MouldRunMaterial, "Material_Item_ID", user)


def create_run(db: Session, data: MouldRunIn, user: User) -> MouldRun:
    conflict = _validate(db, data, None)
    run = MouldRun(Created_By=user.Username)
    with common.flush_unique(db, conflict):
        _apply(run, data, user)
        db.add(run)
    log_change(db, user, MouldRun.__tablename__, common.audit_key(run), None, _snapshot(run))
    return run


def replace_run(db: Session, run_id: int, data: MouldRunIn, user: User) -> MouldRun:
    run = get_run(db, run_id)
    conflict = _validate(db, data, run.MouldRun_ID)
    before = _snapshot(run)
    with common.flush_unique(db, conflict):
        _apply(run, data, user)
        run.Updated_By = user.Username
    log_change(db, user, MouldRun.__tablename__, common.audit_key(run), before, _snapshot(run))
    return run


def set_active(db: Session, run_id: int, active: bool, user: User) -> MouldRun:
    return common.set_active(db, get_run(db, run_id), active, user)
