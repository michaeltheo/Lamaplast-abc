import json
from decimal import Decimal

import pytest
from conftest import audit_rows


@pytest.fixture
def machine(cc_id) -> dict:
    return {"Machine_Code": "ZZT-M01", "Description": "Δοκιμαστική πρέσα ZZT", "Category_Code": "M3", "CC_ID": cc_id,
            "Clamp_Force_tn": 280, "Acquisition_Cost_EUR": "100000", "Residual_Value_EUR": "10000",
            "Useful_Life_Years": 10, "Downtime_Pct": "0.025"}


def create(client, body: dict, **overrides) -> dict:
    response = client.post("/api/machines", json={**body, **overrides})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_create_machine_returns_capacity_and_depreciation_per_hour(admin, machine):
    body = create(admin, machine)

    assert (Decimal(body["Hours_Per_Day"]), body["Days_Per_Year"]) == (Decimal(16), 222)   # defaults
    assert Decimal(body["Annual_Hours"]) == Decimal(3552)                    # 16 × 222
    assert Decimal(body["Depreciation_Per_Hour"]) == Decimal("2.533784")       # 90.000 / (10 × 3.552)


def test_duplicate_code_is_409(admin, machine):
    create(admin, machine)
    response = admin.post("/api/machines", json=machine)
    assert response.status_code == 409
    assert response.json()["message"] == "Ο κωδικός μηχανής ZZT-M01 υπάρχει ήδη"


@pytest.mark.parametrize("patch", [
    {"Category_Code": "ZZ"}, {"CC_ID": 30000}, {"Building_ID": 999999999},
    {"Hours_Per_Day": "24.5"}, {"Hours_Per_Day": "0"}, {"Days_Per_Year": 367},
    {"Downtime_Pct": "1.5"}, {"Residual_Value_EUR": "100000.01"},
])
def test_invalid_machine_is_422(admin, machine, patch):
    assert admin.post("/api/machines", json={**machine, **patch}).status_code == 422


def test_limits_are_inclusive(admin, machine):
    body = create(admin, machine, Hours_Per_Day="24", Days_Per_Year=366, Downtime_Pct="1",
                  Residual_Value_EUR="100000")
    assert Decimal(body["Annual_Hours"]) == Decimal(8784)
    assert Decimal(body["Depreciation_Per_Hour"]) == 0


def test_patch_checks_residual_against_the_stored_cost(admin, machine):
    url = f"/api/machines/{create(admin, machine)['Machine_ID']}"

    assert admin.patch(url, json={"Acquisition_Cost_EUR": "5000"}).status_code == 422     # υπολειμματική 10.000
    patched = admin.patch(url, json={"Hours_Per_Day": "8"})
    assert patched.status_code == 200
    assert Decimal(patched.json()["data"]["Annual_Hours"]) == Decimal(1776)              # ξαναϋπολογίστηκε


def test_resource_must_be_of_type_machine(admin, machine, make_resource):
    wrong = admin.post("/api/machines", json={**machine, "Resource_ID": make_resource("LABOR").Resource_ID})
    assert wrong.status_code == 422
    create(admin, machine, Resource_ID=make_resource("MACHINE").Resource_ID)


def test_list_filters(admin, machine, cc_id):
    create(admin, machine)
    other = create(admin, machine, Machine_Code="ZZT-M02", Category_Code="M5")
    admin.post(f"/api/machines/{other['Machine_ID']}/deactivate")

    def codes(**params):
        items = admin.get("/api/machines", params={"q": "ZZT", **params}).json()["data"]["items"]
        return [m["Machine_Code"] for m in items]
    assert codes() == ["ZZT-M01"]
    assert codes(is_active="false") == ["ZZT-M02"]
    assert codes(category="M3", cc_id=cc_id) == ["ZZT-M01"]
    assert codes(category="M5") == []
    assert codes(building_id=999999999) == []


def test_only_the_machines_module_can_write(user, machine, make_user, login):
    assert user.post("/api/machines", json=machine).status_code == 403
    make_user("test_expert", "EXPERT", modules={"MACHINES": True})
    assert login("test_expert").post("/api/machines", json=machine).status_code == 201


def test_create_and_update_are_audited(admin, machine, db):
    machine_id = create(admin, machine)["Machine_ID"]
    admin.patch(f"/api/machines/{machine_id}", json={"Description": "Άλλη περιγραφή"})

    insert, update = audit_rows(db, "tbl_Machines", f"Machine_ID={machine_id}")
    assert (insert.Action, insert.Username) == ("INSERT", "test_admin")
    assert json.loads(update.Changes_JSON) == {"Description": ["Δοκιμαστική πρέσα ZZT", "Άλλη περιγραφή"]}
