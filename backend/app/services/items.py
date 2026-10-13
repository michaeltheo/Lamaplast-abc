from contextlib import contextmanager

from app.core.audit import log_change, snapshot
from app.models import (
    BSSG,
    BaseMaterial,
    CommercialPillar,
    Customer,
    Item,
    ItemCodeRule,
    LogisticsUnit,
    ProductGroup,
    User,
)
from app.schemas.items import ItemCreate, ItemUpdate, LogisticsUnitIn
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .errors import BusinessRuleError, ConflictError, NotFoundError


def _key(item: Item) -> str:
    return f"Item_ID={item.Item_ID}"


def get_item(db: Session, item_id: int) -> Item:
    # selectinload: τα logistics units έρχονται με ΕΝΑ επιπλέον query, όχι ένα ανά είδος (N+1)
    item = db.scalar(select(Item).where(Item.Item_ID == item_id).options(selectinload(Item.logistics_units)))
    if item is None:
        raise NotFoundError("Το είδος δεν βρέθηκε")
    return item


def items_query(*, q: str | None = None, prefix: str | None = None, group_code: str | None = None,
                bssg_code: str | None = None, customer_id: int | None = None, is_active: bool | None = True,
                is_produced: bool | None = None, is_purchased: bool | None = None) -> Select:
    query = select(Item).order_by(Item.Item_Code)
    if q:
        query = query.where(Item.Item_Code.contains(q, autoescape=True) | Item.Item_Name.contains(q, autoescape=True))
    filters = {
        Item.Item_Category_Prefix: prefix,
        Item.Group_Code: group_code,
        Item.BSSG_Code: bssg_code,
        Item.Customer_ID: customer_id,
        Item.Is_Active: is_active,
        Item.Is_Produced: is_produced,
        Item.Is_Purchased: is_purchased,
    }
    for column, value in filters.items():
        if value is not None:
            query = query.where(column == value)
    return query


# --- κανόνες ---

def _check_code_rule(db: Session, code: str, prefix: str) -> None:
    prefixes = set(db.scalars(select(ItemCodeRule.Prefix)))
    if prefix not in prefixes:
        raise BusinessRuleError(f"Το prefix {prefix} δεν υπάρχει στους κανόνες κωδικοποίησης")
    if not code.startswith(prefix):
        raise BusinessRuleError(f"Ο κωδικός {code} πρέπει να ξεκινά με {prefix}")
    # Τα prefixes επικαλύπτονται (12 και 12699): ισχύει το μακρύτερο που ταιριάζει
    longest = max((p for p in prefixes if code.startswith(p)), key=len)
    if longest != prefix:
        raise BusinessRuleError(f"Ο κωδικός {code} ανήκει στην κατηγορία {longest}, όχι στην {prefix}")


def _check_hierarchy(db: Session, bssg_code: str | None, pillar_code: str | None, group_code: str | None) -> None:
    bssg = db.get(BSSG, bssg_code) if bssg_code else None
    pillar = db.get(CommercialPillar, pillar_code) if pillar_code else None
    group = db.get(ProductGroup, group_code) if group_code else None
    if bssg_code and bssg is None:
        raise BusinessRuleError(f"Το BSSG {bssg_code} δεν υπάρχει")
    if pillar_code and pillar is None:
        raise BusinessRuleError(f"Ο πυλώνας {pillar_code} δεν υπάρχει")
    if group_code and group is None:
        raise BusinessRuleError(f"Η ομάδα {group_code} δεν υπάρχει")

    if group and pillar and group.Pillar_Code != pillar.Pillar_Code:
        raise BusinessRuleError(f"Η ομάδα {group_code} δεν ανήκει στον πυλώνα {pillar_code}")
    parent = pillar or (db.get(CommercialPillar, group.Pillar_Code) if group else None)
    if parent and bssg and parent.BSSG_Code != bssg.BSSG_Code:
        raise BusinessRuleError(f"Ο πυλώνας {parent.Pillar_Code} δεν ανήκει στο BSSG {bssg_code}")


def _check_references(db: Session, values: dict, item_id: int | None) -> None:
    material, customer, fason = values["Base_Material_Code"], values["Customer_ID"], values["Fason_Base_Item_ID"]
    if material is not None and db.get(BaseMaterial, material) is None:
        raise BusinessRuleError(f"Το βασικό υλικό {material} δεν υπάρχει")
    if customer is not None and db.get(Customer, customer) is None:
        raise BusinessRuleError(f"Ο πελάτης με ID {customer} δεν υπάρχει")
    if fason is not None:
        if fason == item_id:
            raise BusinessRuleError("Το είδος δεν μπορεί να είναι φασόν του εαυτού του")
        if db.get(Item, fason) is None:
            raise BusinessRuleError(f"Το βασικό είδος φασόν με ID {fason} δεν υπάρχει")


def _duplicate(code: str) -> ConflictError:
    return ConflictError(f"Ο κωδικός {code} υπάρχει ήδη")


def _validate(db: Session, values: dict, item_id: int | None) -> None:
    """values = όλες οι τιμές που θα έχει το είδος μετά την αλλαγή. Δεν αλλάζει τίποτα στη βάση."""
    code = values["Item_Code"]
    if db.scalar(select(Item.Item_ID).where(Item.Item_Code == code, Item.Item_ID != (item_id or 0))) is not None:
        raise _duplicate(code)
    _check_code_rule(db, code, values["Item_Category_Prefix"])
    _check_hierarchy(db, values["BSSG_Code"], values["Pillar_Code"], values["Group_Code"])
    _check_references(db, values, item_id)


@contextmanager
def _unique_code(db: Session, code: str):
    """Ο έλεγχος του _validate δεν φτάνει αν δύο χρήστες γράψουν τον ίδιο κωδικό ταυτόχρονα:
    τότε αποφασίζει το UNIQUE της βάσης. Το savepoint ακυρώνει μόνο αυτή την εγγραφή."""
    try:
        with db.begin_nested():
            yield
            db.flush()
    except IntegrityError as exc:
        raise _duplicate(code) from exc


# --- εγγραφές (το commit το κάνει ο καλών) ---

def create_item(db: Session, data: ItemCreate, user: User) -> Item:
    values = data.model_dump()
    _validate(db, values, None)
    item = Item(**values, Created_By=user.Username)
    with _unique_code(db, data.Item_Code):
        db.add(item)
    log_change(db, user, Item.__tablename__, _key(item), None, snapshot(item))
    return item


def update_item(db: Session, item_id: int, data: ItemUpdate, user: User) -> Item:
    item = get_item(db, item_id)
    changes = data.model_dump(exclude_unset=True)
    before = snapshot(item)
    after = {**before, **changes}
    _validate(db, after, item.Item_ID)
    with _unique_code(db, after["Item_Code"]):
        for field, value in changes.items():
            setattr(item, field, value)
        item.Updated_By = user.Username
    log_change(db, user, Item.__tablename__, _key(item), before, snapshot(item))
    return item


def set_active(db: Session, item_id: int, active: bool, user: User) -> Item:
    item = get_item(db, item_id)
    if item.Is_Active == active:
        return item
    before = snapshot(item)
    item.Is_Active = active
    item.Updated_By = user.Username
    db.flush()
    log_change(db, user, Item.__tablename__, _key(item), before, snapshot(item))
    return item


def _lu_values(lu: LogisticsUnit) -> dict:
    return {f: getattr(lu, f) for f in LogisticsUnitIn.model_fields if f != "LU_Level"}


def replace_logistics_units(db: Session, item_id: int, units: list[LogisticsUnitIn], user: User) -> Item:
    item = get_item(db, item_id)
    levels = [u.LU_Level for u in units]
    if len(set(levels)) != len(levels):
        raise BusinessRuleError("Το ίδιο LU_Level δόθηκε δύο φορές")

    current = {lu.LU_Level: lu for lu in item.logistics_units}
    before = {f"LU{level}": _lu_values(lu) for level, lu in current.items()}
    # Όσα επίπεδα υπάρχουν ήδη ενημερώνονται στη θέση τους· όσα λείπουν από τη νέα λίστα σβήνονται (delete-orphan)
    for unit in sorted(units, key=lambda u: u.LU_Level):
        lu = current.get(unit.LU_Level)
        if lu is None:
            current[unit.LU_Level] = LogisticsUnit(**unit.model_dump(), Created_By=user.Username)
        elif _lu_values(lu) != unit.model_dump(exclude={"LU_Level"}):
            for field, value in unit.model_dump(exclude={"LU_Level"}).items():
                setattr(lu, field, value)
            lu.Updated_By = user.Username
    item.logistics_units = [current[level] for level in sorted(levels)]
    db.flush()

    after = {f"LU{lu.LU_Level}": _lu_values(lu) for lu in item.logistics_units}
    log_change(db, user, LogisticsUnit.__tablename__, _key(item), before, after)
    return item
