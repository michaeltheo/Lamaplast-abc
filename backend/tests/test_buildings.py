import json
from decimal import Decimal

import pytest
from conftest import audit_rows


@pytest.fixture
def building(cc_id) -> dict:
    return {"Building_Code": "ZZT-B1", "Zone_Name": "Αποθήκη", "Area_m2": "1000", "Height_m": "6",
            "Utilization_Pct": "0.8", "Cost_Basis": "m3", "CC_ID": cc_id,
            "Depreciation_EUR": "12000", "Equipment_Depr_EUR": "3000", "IT_Depr_EUR": "500"}


def test_create_building_returns_the_computed_columns(admin, building):
    response = admin.post("/api/buildings", json=building)

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert (body["Ownership"], body["Floor_Level"], body["Is_Active"]) == ("ΙΔΙΟΚΤΗΤΟ", 0, True)
    assert Decimal(body["Nominal_Volume_m3"]) == Decimal(6000)
    assert Decimal(body["Useful_Volume_m3"]) == Decimal(4800)
    assert Decimal(body["Total_Cost_EUR"]) == Decimal(15500)


def test_same_code_and_zone_is_409_but_another_zone_is_fine(admin, building):
    assert admin.post("/api/buildings", json=building).status_code == 201
    assert admin.post("/api/buildings", json=building).status_code == 409
    assert admin.post("/api/buildings", json={**building, "Zone_Name": "Παραγωγή"}).status_code == 201
    # χωρίς ζώνη: επιτρέπεται μία φορά ανά κτίριο
    assert admin.post("/api/buildings", json={**building, "Zone_Name": None}).status_code == 201
    assert admin.post("/api/buildings", json={**building, "Zone_Name": None}).status_code == 409


@pytest.mark.parametrize("patch", [
    {"Ownership": "ΔΑΝΕΙΚΟ"}, {"Cost_Basis": "kg"}, {"Utilization_Pct": "1.01"}, {"Utilization_Pct": "-0.1"},
    {"CC_ID": 30000}, {"Resource_ID": 999999999},
])
def test_invalid_building_is_422(admin, building, patch):
    assert admin.post("/api/buildings", json={**building, **patch}).status_code == 422


def test_resource_must_be_of_type_building(admin, building, make_resource):
    wrong = admin.post("/api/buildings", json={**building, "Resource_ID": make_resource("MACHINE").Resource_ID})
    assert wrong.status_code == 422
    assert wrong.json()["message"] == "Ο πόρος ZZT-MACHINE είναι τύπου MACHINE, όχι BUILDING"
    right = admin.post("/api/buildings", json={**building, "Resource_ID": make_resource("BUILDING").Resource_ID})
    assert right.status_code == 201


def test_patch_recomputes_and_deactivate_hides_from_the_list(admin, building):
    building_id = admin.post("/api/buildings", json=building).json()["data"]["Building_ID"]

    patched = admin.patch(f"/api/buildings/{building_id}", json={"Utilization_Pct": "0.5"}).json()["data"]
    assert Decimal(patched["Useful_Volume_m3"]) == Decimal(3000)
    assert patched["Zone_Name"] == "Αποθήκη"

    admin.post(f"/api/buildings/{building_id}/deactivate")
    assert admin.get("/api/buildings", params={"q": "ZZT"}).json()["data"]["total"] == 0
    assert admin.get("/api/buildings", params={"q": "ZZT", "is_active": "false"}).json()["data"]["total"] == 1


def test_only_the_buildings_module_can_write(user, building, make_user, login):
    assert user.post("/api/buildings", json=building).status_code == 403
    make_user("test_items", "EXPERT", modules={"ITEMS": True})
    assert login("test_items").post("/api/buildings", json=building).status_code == 403
    make_user("test_expert", "EXPERT", modules={"BUILDINGS": True})
    assert login("test_expert").post("/api/buildings", json=building).status_code == 201


def test_create_and_update_are_audited(admin, building, db):
    building_id = admin.post("/api/buildings", json=building).json()["data"]["Building_ID"]
    admin.patch(f"/api/buildings/{building_id}", json={"Ownership": "ΜΙΣΘΩΜΕΝΟ"})

    insert, update = audit_rows(db, "tbl_Buildings", f"Building_ID={building_id}")
    assert insert.Action == "INSERT"
    assert json.loads(update.Changes_JSON) == {"Ownership": ["ΙΔΙΟΚΤΗΤΟ", "ΜΙΣΘΩΜΕΝΟ"]}
