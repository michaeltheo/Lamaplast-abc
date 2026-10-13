import json
from decimal import Decimal

import pytest
from conftest import audit_rows
from sqlalchemy import select

from app.models import Customer

MOULD = {"Mould_Code": "ZZT-K01", "Mould_Name": "Καλούπι καρέκλας ZZT", "Acquisition_Cost_EUR": "50000",
         "Residual_Value_EUR": "5000", "Life_Cycles": 1_000_000, "Current_Cycles": 250_000}


@pytest.fixture
def customer_id(db) -> int:
    return db.scalar(select(Customer.Customer_ID).where(Customer.Customer_Code == "999"))


def create(client, **overrides) -> dict:
    response = client.post("/api/moulds", json={**MOULD, **overrides})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_create_mould_returns_defaults_and_computed_columns(admin):
    body = create(admin)

    assert (body["Mould_Owner"], body["Mould_Type"], body["Cavities"], body["QC_Factor"]) == ("LAMAPLAST", "SINGLE", 1, 2)
    assert Decimal(body["Depreciable_Value_EUR"]) == Decimal(45000)
    assert Decimal(body["Wear_Pct"]) == Decimal("0.25")
    assert Decimal(body["Depreciation_Per_Cycle"]) == Decimal("0.045")          # 45.000 / 1.000.000 κύκλους
    assert body["warnings"] == []


def test_duplicate_code_is_409(admin):
    create(admin)
    assert admin.post("/api/moulds", json=MOULD).status_code == 409


def test_customer_mould_needs_a_customer(admin, customer_id):
    response = admin.post("/api/moulds", json={**MOULD, "Mould_Owner": "CUSTOMER"})
    assert response.status_code == 422
    assert "Customer_ID" in response.json()["message"]
    assert admin.post("/api/moulds", json={**MOULD, "Mould_Owner": "CUSTOMER", "Customer_ID": 999999999}).status_code == 422

    mould_id = create(admin, Mould_Owner="CUSTOMER", Customer_ID=customer_id)["Mould_ID"]
    # ούτε με PATCH μένει καλούπι πελάτη χωρίς πελάτη
    assert admin.patch(f"/api/moulds/{mould_id}", json={"Customer_ID": None}).status_code == 422
    assert admin.patch(f"/api/moulds/{mould_id}", json={"Customer_ID": None, "Mould_Owner": "LAMAPLAST"}).status_code == 200


@pytest.mark.parametrize(("mould_type", "cavities", "expected"), [
    ("SINGLE", 1, 201), ("SINGLE", 2, 422),
    ("MULTI_CAVITY", 4, 201), ("MULTI_CAVITY", 1, 422),
    ("FAMILY", 2, 201), ("FAMILY", 1, 422),
    ("TWIN", 2, 422),
])
def test_cavities_must_match_the_mould_type(admin, mould_type, cavities, expected):
    response = admin.post("/api/moulds", json={**MOULD, "Mould_Type": mould_type, "Cavities": cavities})
    assert response.status_code == expected


@pytest.mark.parametrize("patch", [
    {"QC_Factor": 0}, {"QC_Factor": 4}, {"Residual_Value_EUR": "50000.01"}, {"Default_Machine_Category": "ZZ"},
    {"Life_Cycles": 0}, {"Item_ID": 999999999},
])
def test_invalid_mould_is_422(admin, patch):
    assert admin.post("/api/moulds", json={**MOULD, **patch}).status_code == 422


def test_exceeding_life_cycles_is_a_warning_not_an_error(admin):
    body = create(admin, Current_Cycles=1_200_000)

    assert Decimal(body["Wear_Pct"]) == Decimal("1.2")
    assert body["warnings"] == ["Το καλούπι έχει ξεπεράσει τη διάρκεια ζωής του (1200000 κύκλοι από 1000000)"]
    patched = admin.patch(f"/api/moulds/{body['Mould_ID']}", json={"Current_Cycles": 900_000}).json()["data"]
    assert (patched["warnings"], Decimal(patched["Wear_Pct"])) == ([], Decimal("0.9"))


def test_item_must_be_a_mould_item(admin, make_item):
    chair = make_item("30ZZT001", "30")
    mould_item = make_item("9801ZZT01", "9801")

    wrong = admin.post("/api/moulds", json={**MOULD, "Item_ID": chair.Item_ID})
    assert wrong.status_code == 422
    assert wrong.json()["message"] == "Το είδος 30ZZT001 δεν είναι είδος καλουπιού"
    assert create(admin, Item_ID=mould_item.Item_ID)["Item_ID"] == mould_item.Item_ID


def test_list_filters(admin, customer_id):
    create(admin)
    other = create(admin, Mould_Code="ZZT-K02", Mould_Owner="CUSTOMER", Customer_ID=customer_id,
                   Mould_Type="FAMILY", Cavities=2)
    admin.post(f"/api/moulds/{other['Mould_ID']}/deactivate")

    def codes(**params):
        items = admin.get("/api/moulds", params={"q": "ZZT", **params}).json()["data"]["items"]
        return [m["Mould_Code"] for m in items]
    assert codes() == ["ZZT-K01"]
    assert codes(is_active="false") == ["ZZT-K02"]
    assert codes(is_active="false", mould_owner="CUSTOMER", mould_type="FAMILY", customer_id=customer_id) == ["ZZT-K02"]
    assert codes(mould_type="FAMILY") == []


def test_only_the_moulds_module_can_write(user, make_user, login):
    assert user.post("/api/moulds", json=MOULD).status_code == 403
    make_user("test_expert", "EXPERT", modules={"MOULDS": True})
    assert login("test_expert").post("/api/moulds", json=MOULD).status_code == 201


def test_create_and_update_are_audited(admin, db):
    mould_id = create(admin)["Mould_ID"]
    admin.patch(f"/api/moulds/{mould_id}", json={"QC_Factor": 3})

    insert, update = audit_rows(db, "tbl_Moulds", f"Mould_ID={mould_id}")
    assert (insert.Action, insert.Username) == ("INSERT", "test_admin")
    assert json.loads(update.Changes_JSON) == {"QC_Factor": [2, 3]}
