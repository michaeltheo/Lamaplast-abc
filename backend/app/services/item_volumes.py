from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.audit import log_change
from app.models import Item, ItemVolume, User
from app.schemas.prices import ItemVolumeIn

from . import common
from .errors import BusinessRuleError

_FIELDS = ("Annual_Qty", "Source")


def volumes_query(db: Session, scenario_id: int, *, item_id: int | None = None) -> Select:
    common.get_scenario(db, scenario_id)
    query = (select(ItemVolume).join(Item, Item.Item_ID == ItemVolume.Item_ID)
             .where(ItemVolume.Scenario_ID == scenario_id).order_by(Item.Item_Code))
    return common.where_equal(query, {ItemVolume.Item_ID: item_id})


def _values(volume) -> dict:
    return {field: getattr(volume, field) for field in _FIELDS}


def upsert_volumes(db: Session, scenario_id: int, volumes: list[ItemVolumeIn], user: User) -> list[ItemVolume]:
    """Ενημερώνει ή προσθέτει τον όγκο κάθε είδους της λίστας. Είδη που δεν είναι στη λίστα δεν αγγίζονται."""
    common.open_scenario(db, scenario_id)
    wanted = {v.Item_ID: v for v in volumes}
    if len(wanted) != len(volumes):
        raise BusinessRuleError("Το ίδιο είδος δόθηκε δύο φορές")
    known = common.item_types(db, wanted)
    for item_id in wanted:
        if item_id not in known:
            raise BusinessRuleError(f"Το είδος με ID {item_id} δεν υπάρχει")

    current = {v.Item_ID: v for v in db.scalars(select(ItemVolume).where(
        ItemVolume.Scenario_ID == scenario_id, ItemVolume.Item_ID.in_(wanted)))}
    before = {str(item_id): _values(v) for item_id, v in current.items()}
    for item_id, new in wanted.items():
        volume = current.get(item_id)
        if volume is None:
            current[item_id] = volume = ItemVolume(Scenario_ID=scenario_id, **new.model_dump(),
                                                   Created_By=user.Username)
            db.add(volume)
        elif _values(volume) != _values(new):
            for field in _FIELDS:
                setattr(volume, field, getattr(new, field))
            volume.Updated_By = user.Username
    db.flush()

    after = {str(item_id): _values(new) for item_id, new in wanted.items()}
    log_change(db, user, ItemVolume.__tablename__, f"Scenario_ID={scenario_id}", before, after)
    return [current[item_id] for item_id in wanted]
