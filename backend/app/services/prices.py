"""Τιμές αγοράς (tbl_Prices) και πώλησης (tbl_SalesPrices). Και οι δύο κρατούν ιστορικό:
κάθε γραμμή ισχύει από Valid_From έως Valid_To (κενό = ακόμα), και για το ίδιο «κλειδί»
(είδος + σενάριο, και πελάτης στις πωλήσεις) τα διαστήματα δεν επικαλύπτονται ποτέ."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Customer, Item, Price, SalesPrice, User
from app.schemas.prices import (
    PriceCreate,
    PriceUpdate,
    SalesPriceCreate,
    SalesPriceUpdate,
)

from . import common
from .errors import BusinessRuleError, ConflictError, NotFoundError

_CONFLICT = ConflictError("Υπάρχει ήδη τιμή με αυτή την ημερομηνία έναρξης")
_PRICE_KEY = ("Item_ID", "Scenario_ID")
_SALES_KEY = ("Item_ID", "Scenario_ID", "Customer_ID")
# Πόσο μπορεί να απέχει το Price_EUR από το Price_Local / FX_Rate (στρογγυλοποιήσεις): 0,1%
_FX_TOLERANCE = Decimal("0.001")
_CENT5 = Decimal("0.00001")


# --- κοινή λογική ιστορικού ---

def _same_key(model, key: tuple[str, ...], values: dict) -> list:
    columns = ((getattr(model, name), values[name]) for name in key)
    return [column == value if value is not None else column.is_(None) for column, value in columns]


def _siblings(db: Session, model, key: tuple[str, ...], values: dict, exclude=None) -> list:
    """Οι άλλες τιμές του ίδιου κλειδιού."""
    rows = db.scalars(select(model).where(*_same_key(model, key, values)).order_by(model.Valid_From))
    return [row for row in rows if row is not exclude]


def _overlaps(a_from: date, a_to: date | None, b_from: date, b_to: date | None) -> bool:
    return a_from <= (b_to or date.max) and b_from <= (a_to or date.max)


def _check_no_overlap(valid_from: date, valid_to: date | None, others: list[tuple[date, date | None]]) -> None:
    for other_from, other_to in others:
        if _overlaps(valid_from, valid_to, other_from, other_to):
            until = f"έως {other_to:%d/%m/%Y}" if other_to else "χωρίς λήξη"
            raise BusinessRuleError(f"Το διάστημα επικαλύπτει την τιμή που ισχύει από {other_from:%d/%m/%Y} {until}")


def _add(db: Session, obj, key: tuple[str, ...], user: User):
    siblings = _siblings(db, type(obj), key, {name: getattr(obj, name) for name in key})
    # Η ανοιχτή τιμή που ξεκίνησε νωρίτερα κλείνει την προηγούμενη μέρα από τη νέα
    to_close = [s for s in siblings if s.Valid_To is None and s.Valid_From < obj.Valid_From]
    closing_day = obj.Valid_From - timedelta(days=1)
    others = [(s.Valid_From, closing_day if s in to_close else s.Valid_To) for s in siblings]
    _check_no_overlap(obj.Valid_From, obj.Valid_To, others)

    for previous in to_close:
        common.update(db, previous, {"Valid_To": closing_day}, user, _CONFLICT)
    return common.insert(db, obj, user, _CONFLICT)


def _patch(db: Session, obj, key: tuple[str, ...], changes: dict, user: User):
    if "Valid_To" in changes:
        valid_to = changes["Valid_To"]
        if valid_to is not None and valid_to < obj.Valid_From:
            raise BusinessRuleError("Το Valid_To δεν μπορεί να είναι πριν από το Valid_From")
        siblings = _siblings(db, type(obj), key, {name: getattr(obj, name) for name in key}, exclude=obj)
        _check_no_overlap(obj.Valid_From, valid_to, [(s.Valid_From, s.Valid_To) for s in siblings])
    return common.update(db, obj, changes, user, _CONFLICT)


def _current(db: Session, model, key: tuple[str, ...], values: dict, on: date):
    return db.scalar(select(model).where(*_same_key(model, key, values), model.Valid_From <= on,
                                         model.Valid_To.is_(None) | (model.Valid_To >= on)))


def _history_query(model, filters: dict, on: date | None) -> Select:
    # ταξινόμηση με τον κωδικό του είδους, και μέσα στο είδος η πιο πρόσφατη τιμή πρώτη
    query = select(model).join(Item, Item.Item_ID == model.Item_ID).order_by(
        Item.Item_Code, model.Valid_From.desc(), *model.__table__.primary_key.columns)
    if on is not None:
        query = query.where(model.Valid_From <= on, model.Valid_To.is_(None) | (model.Valid_To >= on))
    return common.where_equal(query, filters)


def _check_item(db: Session, item_id: int) -> None:
    if db.get(Item, item_id) is None:
        raise BusinessRuleError(f"Το είδος με ID {item_id} δεν υπάρχει")


# --- τιμές αγοράς ---

def get_price(db: Session, price_id: int) -> Price:
    return common.get_or_404(db, Price, price_id, "Η τιμή δεν βρέθηκε")


def prices_query(*, item_id: int | None = None, scenario_id: int | None = None, on: date | None = None) -> Select:
    return _history_query(Price, {Price.Item_ID: item_id, Price.Scenario_ID: scenario_id}, on)


def current_price(db: Session, item_id: int, scenario_id: int, on: date) -> Price:
    price = _current(db, Price, _PRICE_KEY, {"Item_ID": item_id, "Scenario_ID": scenario_id}, on)
    if price is None:
        raise NotFoundError(f"Δεν υπάρχει τιμή σε ισχύ στις {on:%d/%m/%Y}")
    return price


def _resolve_fx(values: dict, fx_was_sent: bool) -> None:
    """Price_EUR = Price_Local / FX_Rate, όπου FX_Rate = μονάδες ξένου νομίσματος ανά 1 EUR."""
    price, local, fx, currency = values["Price_EUR"], values["Price_Local"], values["FX_Rate"], values["Currency"]
    if currency == "EUR":
        if price is None:
            raise BusinessRuleError("Το Price_EUR είναι υποχρεωτικό")
        if fx != 1:
            raise BusinessRuleError("Για τιμή σε EUR το FX_Rate είναι 1")
        if local is not None and local != price:
            raise BusinessRuleError("Για τιμή σε EUR το Price_Local, αν δοθεί, είναι ίσο με το Price_EUR")
        return
    if not fx_was_sent or local is None:
        raise BusinessRuleError(f"Για τιμή σε {currency} χρειάζονται FX_Rate και Price_Local")
    expected = (local / fx).quantize(_CENT5)
    if price is None:
        values["Price_EUR"] = expected
    elif abs(price - expected) > max(_CENT5, expected * _FX_TOLERANCE):
        raise BusinessRuleError(f"Το Price_EUR ({price}) δεν συμφωνεί με Price_Local / FX_Rate = {expected}")


def create_price(db: Session, data: PriceCreate, user: User) -> Price:
    common.open_scenario(db, data.Scenario_ID)
    _check_item(db, data.Item_ID)
    values = data.model_dump()
    _resolve_fx(values, "FX_Rate" in data.model_fields_set)
    return _add(db, Price(**values), _PRICE_KEY, user)


def update_price(db: Session, price_id: int, data: PriceUpdate, user: User) -> Price:
    price = get_price(db, price_id)
    common.open_scenario(db, price.Scenario_ID)
    return _patch(db, price, _PRICE_KEY, data.model_dump(exclude_unset=True), user)


# --- τιμές πώλησης ---

def get_sales_price(db: Session, sales_price_id: int) -> SalesPrice:
    return common.get_or_404(db, SalesPrice, sales_price_id, "Η τιμή πώλησης δεν βρέθηκε")


def sales_prices_query(*, item_id: int | None = None, scenario_id: int | None = None,
                       customer_id: int | None = None, on: date | None = None) -> Select:
    filters = {SalesPrice.Item_ID: item_id, SalesPrice.Scenario_ID: scenario_id, SalesPrice.Customer_ID: customer_id}
    return _history_query(SalesPrice, filters, on)


def current_sales_price(db: Session, item_id: int, scenario_id: int, customer_id: int | None, on: date) -> SalesPrice:
    """Η τιμή του πελάτη· αν δεν έχει δική του, η γενική τιμή (χωρίς πελάτη)."""
    for customer in dict.fromkeys((customer_id, None)):
        key = {"Item_ID": item_id, "Scenario_ID": scenario_id, "Customer_ID": customer}
        price = _current(db, SalesPrice, _SALES_KEY, key, on)
        if price is not None:
            return price
    raise NotFoundError(f"Δεν υπάρχει τιμή πώλησης σε ισχύ στις {on:%d/%m/%Y}")


def create_sales_price(db: Session, data: SalesPriceCreate, user: User) -> SalesPrice:
    common.open_scenario(db, data.Scenario_ID)
    _check_item(db, data.Item_ID)
    if data.Customer_ID is not None and db.get(Customer, data.Customer_ID) is None:
        raise BusinessRuleError(f"Ο πελάτης με ID {data.Customer_ID} δεν υπάρχει")
    return _add(db, SalesPrice(**data.model_dump()), _SALES_KEY, user)


def update_sales_price(db: Session, sales_price_id: int, data: SalesPriceUpdate, user: User) -> SalesPrice:
    price = get_sales_price(db, sales_price_id)
    common.open_scenario(db, price.Scenario_ID)
    return _patch(db, price, _SALES_KEY, data.model_dump(exclude_unset=True), user)
