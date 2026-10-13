from app.core.audit import snapshot
from app.models import Building, User
from app.schemas.buildings import BuildingCreate, BuildingUpdate
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from . import common
from .errors import ConflictError


def get_building(db: Session, building_id: int) -> Building:
    return common.get_or_404(db, Building, building_id, "Το κτίριο δεν βρέθηκε")


def buildings_query(*, q: str | None = None, cc_id: int | None = None, is_active: bool | None = True) -> Select:
    query = select(Building).order_by(Building.Building_Code, Building.Zone_Name)
    query = common.text_search(query, q, Building.Building_Code, Building.Zone_Name)
    return common.where_equal(query, {Building.CC_ID: cc_id, Building.Is_Active: is_active})


def _validate(db: Session, values: dict, building_id: int | None) -> ConflictError:
    """values = όλες οι τιμές που θα έχει το κτίριο μετά την αλλαγή."""
    code, zone = values["Building_Code"], values["Zone_Name"]
    # Μοναδικό είναι το ζεύγος κτίριο + ζώνη: το ίδιο κτίριο μπορεί να έχει πολλές ζώνες
    conflict = ConflictError(f"Το κτίριο {code} με ζώνη {zone} υπάρχει ήδη" if zone
                             else f"Το κτίριο {code} χωρίς ζώνη υπάρχει ήδη")
    same_zone = Building.Zone_Name == zone if zone is not None else Building.Zone_Name.is_(None)
    common.ensure_unique(db, Building.Building_ID, building_id, conflict, Building.Building_Code == code, same_zone)
    common.check_cost_center(db, values["CC_ID"])
    common.check_resource(db, values["Resource_ID"], "BUILDING")
    return conflict


def create_building(db: Session, data: BuildingCreate, user: User) -> Building:
    values = data.model_dump()
    conflict = _validate(db, values, None)
    return common.insert(db, Building(**values), user, conflict)


def update_building(db: Session, building_id: int, data: BuildingUpdate, user: User) -> Building:
    building = get_building(db, building_id)
    changes = data.model_dump(exclude_unset=True)
    conflict = _validate(db, {**snapshot(building), **changes}, building.Building_ID)
    return common.update(db, building, changes, user, conflict)


def set_active(db: Session, building_id: int, active: bool, user: User) -> Building:
    return common.set_active(db, get_building(db, building_id), active, user)
