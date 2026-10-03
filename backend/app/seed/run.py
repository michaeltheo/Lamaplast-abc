"""Γεμίζει τους πίνακες ταξινόμησης και τη δομή ABC.
Τρέχει όσες φορές θέλεις: βρίσκει κάθε γραμμή με τον κωδικό της,
την ενημερώνει αν υπάρχει, την προσθέτει αν δεν υπάρχει.

    python -m app.seed.run
"""
from collections import defaultdict

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import (BSSG, Activity, BaseMaterial, CommercialPillar, CostCenter, Customer, GlobalDefault,
                        ItemCodeRule, MachineCategory, ProductGroup, Resource, ResourceActivity, Scenario)

from . import lookups_data as L
from . import structure_data as S


def upsert(db, model, key: str, rows: list[dict]) -> None:
    """Για κάθε γραμμή: βρες τη με το «key» (π.χ. Item_Code) → ενημέρωσε ή πρόσθεσε."""
    for row in rows:
        obj = db.scalar(select(model).where(getattr(model, key) == row[key]))
        if obj is None:
            db.add(model(**row, Created_By="seed"))
        else:
            for field, value in row.items():
                setattr(obj, field, value)
            obj.Updated_By = "seed"
    db.flush()
    print(f"{model.__tablename__:<26} {len(rows):>3}")


def with_cc_id(rows: list[dict], cc_ids: dict[str, int]) -> list[dict]:
    """Τα δεδομένα γράφουν «CC_Code» (π.χ. "PRD01") → το αλλάζουμε στο CC_ID που έδωσε η βάση."""
    return [{**{k: v for k, v in r.items() if k != "CC_Code"}, "CC_ID": cc_ids[r["CC_Code"]]} for r in rows]


def seed() -> None:
    with SessionLocal() as db:
        # Η σειρά μετράει: πρώτα οι «γονείς»
        upsert(db, GlobalDefault, "Parameter", L.GLOBAL_DEFAULTS)
        upsert(db, ItemCodeRule, "Prefix", L.ITEM_CODE_RULES)
        upsert(db, BaseMaterial, "Material_Code", L.BASE_MATERIALS)
        upsert(db, BSSG, "BSSG_Code", L.BSSG_ROWS)
        upsert(db, CommercialPillar, "Pillar_Code", L.PILLARS)
        upsert(db, ProductGroup, "Group_Code", L.GROUPS)
        upsert(db, MachineCategory, "Category_Code", L.MACHINE_CATEGORIES)
        upsert(db, Customer, "Customer_Code", L.CUSTOMERS)

        # Το CC_ID το δίνει η βάση (autoincrement) → κλειδί είναι ο κωδικός
        upsert(db, CostCenter, "CC_Code", S.COST_CENTERS)
        cc_ids = {c.CC_Code: c.CC_ID for c in db.scalars(select(CostCenter))}
        upsert(db, Activity, "Activity_Code", with_cc_id(S.ACTIVITIES, cc_ids))
        upsert(db, Resource, "Resource_Code", with_cc_id(S.RESOURCES, cc_ids))

        # Σενάρια: πρώτα χωρίς βασικό σενάριο, μετά συνδέουμε το Base με ID
        upsert(db, Scenario, "Scenario_Name", [{k: v for k, v in r.items() if k != "Base"} for r in S.SCENARIOS])
        ids = {s.Scenario_Name: s.Scenario_ID for s in db.scalars(select(Scenario))}
        for r in S.SCENARIOS:
            if r.get("Base"):
                db.get(Scenario, ids[r["Scenario_Name"]]).Base_Scenario_ID = ids[r["Base"]]

        # Κατανομή πόρων σε δραστηριότητες για το σενάριο S.ALLOCATION_SCENARIO
        if S.RESOURCE_ACTIVITY:
            scenario_id = ids[S.ALLOCATION_SCENARIO]
            res = {r.Resource_Code: r.Resource_ID for r in db.scalars(select(Resource))}
            act = {a.Activity_Code: a.Activity_ID for a in db.scalars(select(Activity))}
            totals = defaultdict(float)
            for r in S.RESOURCE_ACTIVITY:
                pk = (scenario_id, res[r["Resource"]], act[r["Activity"]])
                obj = db.get(ResourceActivity, pk) or ResourceActivity(
                    Scenario_ID=pk[0], Resource_ID=pk[1], Activity_ID=pk[2], Created_By="seed")
                obj.Share_Pct, obj.Allocation_Basis = r["Share_Pct"], r.get("Allocation_Basis")
                db.add(obj)
                totals[r["Resource"]] += float(r["Share_Pct"])
            bad = {k: v for k, v in totals.items() if abs(v - 1) > 1e-9}
            print(f"{ResourceActivity.__tablename__:<26} {len(S.RESOURCE_ACTIVITY):>3}",
                  "✓ όλα 100%" if not bad else f"⚠ όχι 100%: {bad}")

        db.commit()


if __name__ == "__main__":
    seed()
