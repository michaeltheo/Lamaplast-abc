"""Τα βήματα που επαναλαμβάνονται σε κάθε master: εύρεση, φίλτρα, εγγραφή με audit, ενεργό/ανενεργό."""
from contextlib import contextmanager
from decimal import Decimal

from app.core.audit import log_change, snapshot
from app.models import CostCenter, Item, ItemCodeRule, Resource, Scenario, User
from sqlalchemy import Select, inspect, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .errors import BusinessRuleError, ConflictError, NotFoundError


def audit_key(obj) -> str:
    """π.χ. "Machine_ID=7": το κλειδί της γραμμής στο tbl_AuditLog."""
    column = inspect(obj).mapper.primary_key[0]
    return f"{column.name}={getattr(obj, column.name)}"


def get_or_404(db: Session, model, pk, message: str):
    obj = db.get(model, pk)
    if obj is None:
        raise NotFoundError(message)
    return obj


# --- λίστες ---

def where_equal(query: Select, filters: dict) -> Select:
    """Φίλτρα «στήλη = τιμή»· όσα είναι None αγνοούνται."""
    for column, value in filters.items():
        if value is not None:
            query = query.where(column == value)
    return query


def text_search(query: Select, q: str | None, *columns) -> Select:
    if not q:
        return query
    return query.where(or_(*(column.contains(q, autoescape=True) for column in columns)))


# --- έλεγχοι ---

def ensure_unique(db: Session, pk_column, pk: int | None, conflict: ConflictError, *where) -> None:
    """Υπάρχει ΑΛΛΗ γραμμή (όχι η pk) που ταιριάζει στο where; → 409."""
    if db.scalar(select(pk_column).where(*where, pk_column != (pk or 0))) is not None:
        raise conflict


def check_cost_center(db: Session, cc_id: int) -> None:
    if db.get(CostCenter, cc_id) is None:
        raise BusinessRuleError(f"Το κέντρο κόστους με ID {cc_id} δεν υπάρχει")


def check_resource(db: Session, resource_id: int | None, resource_type: str) -> None:
    if resource_id is None:
        return
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise BusinessRuleError(f"Ο πόρος με ID {resource_id} δεν υπάρχει")
    if resource.Resource_Type != resource_type:
        raise BusinessRuleError(
            f"Ο πόρος {resource.Resource_Code} είναι τύπου {resource.Resource_Type}, όχι {resource_type}")


def get_scenario(db: Session, scenario_id: int) -> Scenario:
    return get_or_404(db, Scenario, scenario_id, "Το σενάριο δεν βρέθηκε")


def open_scenario(db: Session, scenario_id: int) -> Scenario:
    """Για εγγραφές: σε κλειδωμένο σενάριο δεν αλλάζει τίποτα."""
    scenario = get_scenario(db, scenario_id)
    if scenario.Is_Locked:
        raise BusinessRuleError(f"Το σενάριο {scenario.Scenario_Name} είναι κλειδωμένο")
    return scenario


def item_types(db: Session, item_ids) -> dict[int, tuple[str, str, bool]]:
    """Item_ID → (Item_Code, Item_Type του prefix του, Is_Purchased), με ένα query για όλα τα είδη."""
    rows = db.execute(select(Item.Item_ID, Item.Item_Code, ItemCodeRule.Item_Type, Item.Is_Purchased)
                      .join(ItemCodeRule, ItemCodeRule.Prefix == Item.Item_Category_Prefix)
                      .where(Item.Item_ID.in_(set(item_ids))))
    return {item_id: (code, item_type, purchased) for item_id, code, item_type, purchased in rows}


# --- ποσοστά που πρέπει να αθροίζουν 100% ---

def is_whole(total: Decimal, tolerance: Decimal) -> bool:
    return abs(total - 1) <= tolerance


def pct_text(value: Decimal) -> str:
    """0.95 → "95,00%". Κρατάει 4 δεκαδικά μόνο όταν χρειάζονται (99,9999%)."""
    return f"{value * 100:.4f}".removesuffix("00").replace(".", ",") + "%"


# --- εγγραφές (το commit το κάνει ο καλών) ---

@contextmanager
def flush_unique(db: Session, conflict: ConflictError):
    """Ο έλεγχος πριν την εγγραφή δεν φτάνει αν δύο χρήστες γράψουν ταυτόχρονα: τότε αποφασίζει
    το UNIQUE της βάσης. Το savepoint ακυρώνει μόνο αυτή την εγγραφή."""
    try:
        with db.begin_nested():
            yield
            db.flush()
    except IntegrityError as exc:
        raise conflict from exc


def insert(db: Session, obj, user: User, conflict: ConflictError):
    obj.Created_By = user.Username
    with flush_unique(db, conflict):
        db.add(obj)
    log_change(db, user, obj.__tablename__, audit_key(obj), None, snapshot(obj))
    return obj


def update(db: Session, obj, changes: dict, user: User, conflict: ConflictError):
    before = snapshot(obj)
    with flush_unique(db, conflict):
        for field, value in changes.items():
            setattr(obj, field, value)
        obj.Updated_By = user.Username
    log_change(db, user, obj.__tablename__, audit_key(obj), before, snapshot(obj))
    return obj


def set_active(db: Session, obj, active: bool, user: User):
    if obj.Is_Active == active:
        return obj
    before = snapshot(obj)
    obj.Is_Active = active
    obj.Updated_By = user.Username
    db.flush()
    log_change(db, user, obj.__tablename__, audit_key(obj), before, snapshot(obj))
    return obj
