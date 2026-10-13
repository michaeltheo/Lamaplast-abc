from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Customer, User
from app.schemas.customers import CustomerCreate, CustomerUpdate

from . import common
from .errors import ConflictError


def get_customer(db: Session, customer_id: int) -> Customer:
    return common.get_or_404(db, Customer, customer_id, "Ο πελάτης δεν βρέθηκε")


def customers_query(*, q: str | None = None, is_internal: bool | None = None,
                    is_active: bool | None = True) -> Select:
    query = select(Customer).order_by(Customer.Customer_Code)
    query = common.text_search(query, q, Customer.Customer_Code, Customer.Customer_Name)
    return common.where_equal(query, {Customer.Is_Internal: is_internal, Customer.Is_Active: is_active})


def _validate(db: Session, values: dict, customer_id: int | None) -> ConflictError:
    code = values["Customer_Code"]
    conflict = ConflictError(f"Ο κωδικός πελάτη {code} υπάρχει ήδη")
    common.ensure_unique(db, Customer.Customer_ID, customer_id, conflict, Customer.Customer_Code == code)
    return conflict


def create_customer(db: Session, data: CustomerCreate, user: User) -> Customer:
    values = data.model_dump()
    conflict = _validate(db, values, None)
    return common.insert(db, Customer(**values), user, conflict)


def update_customer(db: Session, customer_id: int, data: CustomerUpdate, user: User) -> Customer:
    customer = get_customer(db, customer_id)
    changes = data.model_dump(exclude_unset=True)
    conflict = _validate(db, {"Customer_Code": customer.Customer_Code, **changes}, customer.Customer_ID)
    return common.update(db, customer, changes, user, conflict)


def set_active(db: Session, customer_id: int, active: bool, user: User) -> Customer:
    return common.set_active(db, get_customer(db, customer_id), active, user)
