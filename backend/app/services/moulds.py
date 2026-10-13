from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.audit import snapshot
from app.models import Customer, MachineCategory, Mould, User
from app.schemas.moulds import MouldCreate, MouldUpdate

from . import common
from .errors import BusinessRuleError, ConflictError


def get_mould(db: Session, mould_id: int) -> Mould:
    return common.get_or_404(db, Mould, mould_id, "Το καλούπι δεν βρέθηκε")


def moulds_query(*, q: str | None = None, mould_owner: str | None = None, mould_type: str | None = None,
                 customer_id: int | None = None, is_active: bool | None = True) -> Select:
    query = select(Mould).order_by(Mould.Mould_Code)
    query = common.text_search(query, q, Mould.Mould_Code, Mould.Mould_Name)
    return common.where_equal(query, {Mould.Mould_Owner: mould_owner, Mould.Mould_Type: mould_type,
                                      Mould.Customer_ID: customer_id, Mould.Is_Active: is_active})


def _validate(db: Session, values: dict, mould_id: int | None) -> ConflictError:
    """values = όλες οι τιμές που θα έχει το καλούπι μετά την αλλαγή."""
    code = values["Mould_Code"]
    conflict = ConflictError(f"Ο κωδικός καλουπιού {code} υπάρχει ήδη")
    common.ensure_unique(db, Mould.Mould_ID, mould_id, conflict, Mould.Mould_Code == code)

    customer_id = values["Customer_ID"]
    if values["Mould_Owner"] == "CUSTOMER" and customer_id is None:
        raise BusinessRuleError("Καλούπι πελάτη (Mould_Owner = CUSTOMER) χρειάζεται Customer_ID")
    if customer_id is not None and db.get(Customer, customer_id) is None:
        raise BusinessRuleError(f"Ο πελάτης με ID {customer_id} δεν υπάρχει")

    mould_type, cavities = values["Mould_Type"], values["Cavities"]
    if mould_type == "SINGLE" and cavities != 1:
        raise BusinessRuleError("Καλούπι SINGLE έχει ακριβώς 1 κοιλότητα")
    if mould_type != "SINGLE" and cavities < 2:
        raise BusinessRuleError(f"Καλούπι {mould_type} έχει τουλάχιστον 2 κοιλότητες")

    if values["Residual_Value_EUR"] > values["Acquisition_Cost_EUR"]:
        raise BusinessRuleError("Η υπολειμματική αξία δεν μπορεί να ξεπερνά το κόστος κτήσης")
    # Η υπέρβαση της ζωής του καλουπιού είναι μόνο warning· εδώ κόβουμε ό,τι δεν χωράει στο Wear_Pct
    life = values["Life_Cycles"]
    if life is not None and values["Current_Cycles"] >= life * 1000:
        raise BusinessRuleError("Το Current_Cycles είναι υπερβολικά μεγάλο σε σχέση με το Life_Cycles")

    category = values["Default_Machine_Category"]
    if category is not None and db.get(MachineCategory, category) is None:
        raise BusinessRuleError(f"Η κατηγορία μηχανής {category} δεν υπάρχει")

    item_id = values["Item_ID"]
    if item_id is not None:
        info = common.item_types(db, [item_id]).get(item_id)
        if info is None:
            raise BusinessRuleError(f"Το είδος με ID {item_id} δεν υπάρχει")
        if info[1] != "MOULD":
            raise BusinessRuleError(f"Το είδος {info[0]} δεν είναι είδος καλουπιού")
    return conflict


def create_mould(db: Session, data: MouldCreate, user: User) -> Mould:
    values = data.model_dump()
    conflict = _validate(db, values, None)
    return common.insert(db, Mould(**values), user, conflict)


def update_mould(db: Session, mould_id: int, data: MouldUpdate, user: User) -> Mould:
    mould = get_mould(db, mould_id)
    changes = data.model_dump(exclude_unset=True)
    conflict = _validate(db, {**snapshot(mould), **changes}, mould.Mould_ID)
    return common.update(db, mould, changes, user, conflict)


def set_active(db: Session, mould_id: int, active: bool, user: User) -> Mould:
    return common.set_active(db, get_mould(db, mould_id), active, user)
