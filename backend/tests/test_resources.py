import json
from decimal import Decimal

import pytest
from conftest import audit_rows

from app.models import Activity, ResourceActivity


@pytest.fixture
def resource(cc_id) -> dict:
    return {"Resource_Code": "ZZT-RES-1", "Resource_Name": "Προσωπικό ενέσιμων ZZT", "CC_ID": cc_id,
            "Resource_Type": "LABOR"}


@pytest.fixture
def resource_id(admin, resource) -> int:
    return create(admin, resource)["Resource_ID"]


@pytest.fixture
def scenario_id(make_scenario) -> int:
    return make_scenario().Scenario_ID


def create(client, body: dict, **overrides) -> dict:
    response = client.post("/api/resources", json={**body, **overrides})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def put_shares(client, resource_id: int, scenario_id: int, activity_ids: list[int], shares: list[str]):
    body = [{"Activity_ID": a, "Share_Pct": s} for a, s in zip(activity_ids, shares, strict=False)]
    return client.put(f"/api/resources/{resource_id}/activities", params={"scenario_id": scenario_id}, json=body)


# --- CRUD του πόρου ---

def test_create_resource_is_201(admin, resource):
    body = create(admin, resource)
    assert (body["Resource_Code"], body["Resource_Type"], body["Is_Active"]) == ("ZZT-RES-1", "LABOR", True)


def test_duplicate_code_is_409(admin, resource):
    create(admin, resource)
    assert admin.post("/api/resources", json=resource).status_code == 409


@pytest.mark.parametrize("patch", [{"Resource_Type": "ROBOT"}, {"CC_ID": 30000}, {"Resource_Code": ""}])
def test_invalid_resource_is_422(admin, resource, patch):
    assert admin.post("/api/resources", json={**resource, **patch}).status_code == 422


def test_type_cannot_change_while_a_machine_uses_the_resource(admin, resource, cc_id):
    resource_id = create(admin, resource, Resource_Type="MACHINE")["Resource_ID"]
    url = f"/api/resources/{resource_id}"
    assert admin.patch(url, json={"Resource_Type": "OVERHEAD"}).status_code == 200
    assert admin.patch(url, json={"Resource_Type": "MACHINE"}).status_code == 200

    machine = {"Machine_Code": "ZZT-M01", "Description": "Πρέσα", "Category_Code": "M3", "CC_ID": cc_id,
               "Resource_ID": resource_id}
    assert admin.post("/api/machines", json=machine).status_code == 201
    assert admin.patch(url, json={"Resource_Type": "LABOR"}).status_code == 422
    assert admin.patch(url, json={"Resource_Name": "Άλλο όνομα"}).status_code == 200


def test_list_filters(admin, resource):
    create(admin, resource)
    other = create(admin, resource, Resource_Code="ZZT-RES-2", Resource_Type="OVERHEAD")
    admin.post(f"/api/resources/{other['Resource_ID']}/deactivate")

    def codes(**params):
        items = admin.get("/api/resources", params={"q": "ZZT", **params}).json()["data"]["items"]
        return [r["Resource_Code"] for r in items]
    assert codes() == ["ZZT-RES-1"]
    assert codes(is_active="false") == ["ZZT-RES-2"]
    assert codes(resource_type="OVERHEAD") == []
    assert admin.get("/api/resources", params={"resource_type": "ROBOT"}).status_code == 422


def test_only_the_cost_structure_module_can_write(user, resource, make_user, login, make_scenario, activity_ids):
    assert user.post("/api/resources", json=resource).status_code == 403
    make_user("test_expert", "EXPERT", modules={"COST_STRUCTURE": True})
    resource_id = create(login("test_expert"), resource)["Resource_ID"]
    # ο USER διαβάζει τα ποσοστά αλλά δεν τα αλλάζει
    scenario_id = make_scenario().Scenario_ID
    assert put_shares(user, resource_id, scenario_id, activity_ids, ["1"]).status_code == 403
    assert user.get(f"/api/resources/{resource_id}/activities", params={"scenario_id": scenario_id}).status_code == 200


def test_create_and_update_are_audited(admin, resource, db):
    resource_id = create(admin, resource)["Resource_ID"]
    admin.patch(f"/api/resources/{resource_id}", json={"Resource_Name": "Άλλο όνομα"})

    insert, update = audit_rows(db, "tbl_Resources", f"Resource_ID={resource_id}")
    assert (insert.Action, insert.Username) == ("INSERT", "test_admin")
    assert json.loads(update.Changes_JSON) == {"Resource_Name": ["Προσωπικό ενέσιμων ZZT", "Άλλο όνομα"]}


# --- ο κανόνας 100% ---

@pytest.mark.parametrize(("shares", "expected"), [
    (["0.5", "0.3", "0.1999"], 422),       # 99,99%
    (["0.5", "0.3", "0.2"], 200),          # 100%
    (["0.5", "0.3", "0.2001"], 422),       # 100,01%
    (["0.5", "0.3", "0.199999"], 200),     # 99,9999%: μέσα στην ανοχή ±0.000001
    (["0.5", "0.3", "0.200001"], 200),     # 100,0001%: μέσα στην ανοχή
    (["0.5", "0.3", "0.199998"], 422),     # 99,9998%: έξω από την ανοχή
    (["0.5", "0.3", "0.200002"], 422),     # 100,0002%: έξω από την ανοχή
])
def test_shares_must_sum_to_100_percent(admin, resource_id, scenario_id, activity_ids, shares, expected):
    assert put_shares(admin, resource_id, scenario_id, activity_ids, shares).status_code == expected


def test_the_message_names_the_resource_and_the_total(admin, resource_id, scenario_id, activity_ids):
    response = put_shares(admin, resource_id, scenario_id, activity_ids, ["0.8", "0.15"])
    assert response.status_code == 422
    assert response.json()["message"] == "Τα ποσοστά του πόρου ZZT-RES-1 αθροίζουν 95,00% (πρέπει 100%)"


def test_put_replaces_the_whole_list_and_is_audited(admin, resource_id, scenario_id, activity_ids, db):
    running, setup, qc = activity_ids
    url, params = f"/api/resources/{resource_id}/activities", {"scenario_id": scenario_id}
    assert put_shares(admin, resource_id, scenario_id, [running, setup], ["0.8", "0.2"]).status_code == 200

    response = put_shares(admin, resource_id, scenario_id, [running, qc], ["0.7", "0.3"])

    assert response.status_code == 200
    stored = {s["Activity_ID"]: Decimal(s["Share_Pct"]) for s in admin.get(url, params=params).json()["data"]}
    assert stored == {running: Decimal("0.7"), qc: Decimal("0.3")}
    assert [s["Activity_ID"] for s in response.json()["data"]] == [running, qc]

    first, second = audit_rows(db, "tbl_ResourceActivities", f"Resource_ID={resource_id};Scenario_ID={scenario_id}")
    # όπως στα δικαιώματα χρηστών: η αλλαγή λίστας γράφεται ως UPDATE του γονιού, με [παλιό, νέο] ανά γραμμή
    assert json.loads(first.Changes_JSON)[str(setup)][0] is None
    changes = json.loads(second.Changes_JSON)
    assert set(changes) == {str(running), str(setup), str(qc)}
    assert changes[str(setup)][1] is None and changes[str(qc)][0] is None
    assert (changes[str(running)][0]["Share_Pct"], changes[str(running)][1]["Share_Pct"]) == ("0.800000", "0.7")


def test_shares_are_kept_per_scenario(admin, resource_id, scenario_id, activity_ids, make_scenario):
    other = make_scenario("ZZT άλλο").Scenario_ID
    put_shares(admin, resource_id, scenario_id, activity_ids, ["1"])
    assert put_shares(admin, resource_id, other, activity_ids, ["0.6", "0.4"]).status_code == 200

    url = f"/api/resources/{resource_id}/activities"
    assert len(admin.get(url, params={"scenario_id": scenario_id}).json()["data"]) == 1
    assert len(admin.get(url, params={"scenario_id": other}).json()["data"]) == 2
    # άδεια λίστα: ο πόρος μένει χωρίς κατανομή σε αυτό το σενάριο
    assert put_shares(admin, resource_id, other, [], []).json()["data"] == []
    assert len(admin.get(url, params={"scenario_id": scenario_id}).json()["data"]) == 1


def test_invalid_shares_are_422(admin, resource_id, scenario_id, activity_ids, db):
    running, setup, qc = activity_ids
    assert put_shares(admin, resource_id, scenario_id, [running, running], ["0.5", "0.5"]).status_code == 422
    assert put_shares(admin, resource_id, scenario_id, [999999999], ["1"]).status_code == 422
    assert put_shares(admin, resource_id, scenario_id, [running, setup], ["1", "0"]).status_code == 422
    assert put_shares(admin, resource_id, scenario_id, [running], ["1.1"]).status_code == 422

    db.get(Activity, qc).Is_Active = False
    db.flush()
    response = put_shares(admin, resource_id, scenario_id, [running, qc], ["0.5", "0.5"])
    assert response.status_code == 422
    assert "ανενεργή" in response.json()["message"]


def test_locked_or_unknown_scenario(admin, resource_id, activity_ids, make_scenario):
    locked = make_scenario("ZZT κλειδωμένο", locked=True).Scenario_ID
    url = f"/api/resources/{resource_id}/activities"

    response = put_shares(admin, resource_id, locked, activity_ids, ["1"])
    assert response.status_code == 422
    assert response.json()["message"] == "Το σενάριο ZZT κλειδωμένο είναι κλειδωμένο"
    assert admin.get(url, params={"scenario_id": locked}).status_code == 200       # η ανάγνωση επιτρέπεται
    assert put_shares(admin, resource_id, 999999999, activity_ids, ["1"]).status_code == 404
    assert admin.get(url).status_code == 422                                       # το scenario_id είναι υποχρεωτικό
    assert admin.get("/api/resources/999999999/activities", params={"scenario_id": locked}).status_code == 404


# --- allocation-check ---

def test_allocation_check_lists_resources_that_are_not_100_percent(admin, resource, scenario_id, activity_ids, db):
    complete = create(admin, resource, Resource_Code="ZZT-OK")["Resource_ID"]
    short = create(admin, resource, Resource_Code="ZZT-SHORT")["Resource_ID"]
    create(admin, resource, Resource_Code="ZZT-EMPTY")
    inactive = create(admin, resource, Resource_Code="ZZT-OFF")["Resource_ID"]
    admin.post(f"/api/resources/{inactive}/deactivate")
    put_shares(admin, complete, scenario_id, activity_ids, ["0.5", "0.5"])
    # 95% δεν περνάει από το API· μπαίνει κατευθείαν στη βάση, όπως θα έμπαινε από παλιό import
    db.add(ResourceActivity(Scenario_ID=scenario_id, Resource_ID=short, Activity_ID=activity_ids[0],
                            Share_Pct=Decimal("0.95")))
    db.flush()

    response = admin.get("/api/resources/allocation-check", params={"scenario_id": scenario_id})

    assert response.status_code == 200
    issues = {i["Resource_Code"]: i for i in response.json()["data"] if i["Resource_Code"].startswith("ZZT")}
    assert set(issues) == {"ZZT-SHORT", "ZZT-EMPTY"}
    assert issues["ZZT-SHORT"]["Message"] == "Αθροίζει 95,00% (πρέπει 100%)"
    assert Decimal(issues["ZZT-SHORT"]["Total_Share_Pct"]) == Decimal("0.95")
    assert (issues["ZZT-EMPTY"]["Activities"], issues["ZZT-EMPTY"]["Message"]) == (0, "Δεν έχει ποσοστά")
    assert admin.get("/api/resources/allocation-check", params={"scenario_id": 999999999}).status_code == 404
