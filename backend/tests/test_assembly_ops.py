import json
from decimal import Decimal

import pytest
from conftest import audit_rows


@pytest.fixture
def op(make_item, activity_ids) -> dict:
    return {"AssemblyOp_Code": "ZZT-AS-1", "Item_ID": make_item("30ZZT001", "30").Item_ID,
            "Operation_Name": "Συναρμολόγηση καρέκλας ZZT", "Activity_ID": activity_ids[0],
            "Workers_Per_Cell": "2", "Units_Per_Hour": "120"}


def create(client, body: dict, **overrides) -> dict:
    response = client.post("/api/assembly-ops", json={**body, **overrides})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_create_op_returns_time_and_labour_per_unit(admin, op):
    body = create(admin, op)

    assert (body["Operation_Type"], body["Sequence"], body["Is_Active"]) == ("OWN", 10, True)
    assert Decimal(body["Sec_Per_Unit"]) == Decimal(30)                     # 3600 / 120 τεμάχια την ώρα
    assert Decimal(body["Labor_Hrs_Per_Unit"]) == Decimal("0.016667")       # 2 εργάτες / 120 τεμάχια


def test_duplicate_code_is_409(admin, op):
    create(admin, op)
    assert admin.post("/api/assembly-ops", json=op).status_code == 409


@pytest.mark.parametrize("patch", [
    {"Units_Per_Hour": "0"}, {"Workers_Per_Cell": "0"}, {"Operation_Type": "OUTSOURCED"},
    {"Activity_ID": 999999999}, {"Item_ID": 999999999},
])
def test_invalid_op_is_422(admin, op, patch):
    assert admin.post("/api/assembly-ops", json={**op, **patch}).status_code == 422


def test_patch_recomputes_and_activity_is_optional(admin, op):
    op_id = create(admin, op, Operation_Type="FASON", Activity_ID=None)["AssemblyOp_ID"]

    patched = admin.patch(f"/api/assembly-ops/{op_id}", json={"Units_Per_Hour": "60"}).json()["data"]
    assert (Decimal(patched["Sec_Per_Unit"]), patched["Operation_Type"], patched["Activity_ID"]) == (60, "FASON", None)
    assert admin.patch(f"/api/assembly-ops/{op_id}", json={"Units_Per_Hour": None}).status_code == 422


def test_list_filters(admin, op):
    create(admin, op)
    other = create(admin, op, AssemblyOp_Code="ZZT-AS-2", Operation_Type="FASON")
    admin.post(f"/api/assembly-ops/{other['AssemblyOp_ID']}/deactivate")

    def codes(**params):
        items = admin.get("/api/assembly-ops", params={"q": "ZZT", **params}).json()["data"]["items"]
        return [o["AssemblyOp_Code"] for o in items]
    assert codes() == ["ZZT-AS-1"]
    assert codes(item_id=op["Item_ID"], is_active="false", operation_type="FASON") == ["ZZT-AS-2"]
    assert codes(operation_type="FASON") == []


def test_only_the_moulds_module_can_write(user, op, make_user, login):
    assert user.post("/api/assembly-ops", json=op).status_code == 403
    make_user("test_expert", "EXPERT", modules={"MOULDS": True})
    create(login("test_expert"), op)


def test_create_and_update_are_audited(admin, op, db):
    op_id = create(admin, op)["AssemblyOp_ID"]
    admin.patch(f"/api/assembly-ops/{op_id}", json={"Sequence": 20})

    insert, update = audit_rows(db, "tbl_AssemblyOps", f"AssemblyOp_ID={op_id}")
    assert (insert.Action, insert.Username) == ("INSERT", "test_admin")
    assert json.loads(update.Changes_JSON) == {"Sequence": [10, 20]}
