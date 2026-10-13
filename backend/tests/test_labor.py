import json
from decimal import Decimal

import pytest
from conftest import audit_rows


@pytest.fixture
def employee(cc_id) -> dict:
    return {"Employee_Code": "ZZT-E01", "Employee_Name": "Δοκιμαστικός Εργαζόμενος", "Labor_Category": "Χειριστής ZZT",
            "CC_ID": cc_id, "Annual_Cost_EUR": "21312", "Utilization_Rate": "0.947"}


def create(client, body: dict, **overrides) -> dict:
    response = client.post("/api/labor", json={**body, **overrides})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_create_employee_returns_the_nominal_rate(admin, employee):
    body = create(admin, employee)

    assert Decimal(body["Max_Hours_Year"]) == Decimal(1776)                # default
    assert Decimal(body["Nominal_Rate_EUR_h"]) == Decimal(12)              # 21.312 / 1.776
    assert body["Employee_Name"] == "Δοκιμαστικός Εργαζόμενος"


def test_actual_hours_replace_max_hours_in_the_rate(admin, employee):
    body = create(admin, employee, Actual_Hours_Year="1600")
    assert Decimal(body["Nominal_Rate_EUR_h"]) == Decimal("13.32")           # 21.312 / 1.600


def test_duplicate_code_is_409(admin, employee):
    create(admin, employee)
    assert admin.post("/api/labor", json=employee).status_code == 409


@pytest.mark.parametrize("patch", [
    {"Annual_Cost_EUR": "-1"}, {"Utilization_Rate": "1.21"}, {"Utilization_Rate": "-0.1"},
    {"Max_Hours_Year": "0"}, {"CC_ID": 30000}, {"Resource_ID": 999999999},
])
def test_invalid_employee_is_422(admin, employee, patch):
    assert admin.post("/api/labor", json={**employee, **patch}).status_code == 422


def test_limits_follow_the_database_checks(admin, employee):
    # η βάση δέχεται κόστος 0 και απασχόληση έως 1.2 (υπερωρίες)
    create(admin, employee, Annual_Cost_EUR="0", Utilization_Rate="1.2")


def test_resource_must_be_of_type_labor(admin, employee, make_resource):
    wrong = admin.post("/api/labor", json={**employee, "Resource_ID": make_resource("MACHINE").Resource_ID})
    assert wrong.status_code == 422
    create(admin, employee, Resource_ID=make_resource("LABOR").Resource_ID)


# --- GDPR ---

def test_user_role_never_sees_employee_names(admin, user, employee):
    employee_id = create(admin, employee)["Employee_ID"]

    listed = user.get("/api/labor", params={"q": "ZZT"}).json()["data"]["items"]
    assert [(e["Employee_Code"], e["Employee_Name"]) for e in listed] == [("ZZT-E01", None)]
    assert Decimal(listed[0]["Annual_Cost_EUR"]) == Decimal(21312)         # τα υπόλοιπα πεδία φαίνονται
    assert user.get(f"/api/labor/{employee_id}").json()["data"]["Employee_Name"] is None
    # ούτε με αναζήτηση: το q του USER δεν ψάχνει στα ονόματα
    assert user.get("/api/labor", params={"q": "Δοκιμαστικός"}).json()["data"]["total"] == 0


def test_admin_and_expert_see_and_search_employee_names(admin, employee, make_user, login):
    employee_id = create(admin, employee)["Employee_ID"]
    make_user("test_expert", "EXPERT")

    for client in (admin, login("test_expert")):
        listed = client.get("/api/labor", params={"q": "Δοκιμαστικός"}).json()["data"]["items"]
        assert [e["Employee_Name"] for e in listed] == ["Δοκιμαστικός Εργαζόμενος"]
        assert client.get(f"/api/labor/{employee_id}").json()["data"]["Employee_Name"] == "Δοκιμαστικός Εργαζόμενος"


# --- δικαιώματα / audit ---

def test_only_the_labor_module_can_write(user, employee, make_user, login):
    assert user.post("/api/labor", json=employee).status_code == 403
    make_user("test_expert", "EXPERT", modules={"LABOR": True})
    assert login("test_expert").post("/api/labor", json=employee).status_code == 201


def test_anonymous_gets_401(client):
    assert client.get("/api/labor").status_code == 401


def test_deactivate_hides_from_the_default_list(admin, employee):
    employee_id = create(admin, employee)["Employee_ID"]
    admin.post(f"/api/labor/{employee_id}/deactivate")
    assert admin.get("/api/labor", params={"q": "ZZT"}).json()["data"]["total"] == 0
    assert admin.get("/api/labor", params={"q": "ZZT", "is_active": "false"}).json()["data"]["total"] == 1


def test_create_and_update_are_audited(admin, employee, db):
    employee_id = create(admin, employee)["Employee_ID"]
    admin.patch(f"/api/labor/{employee_id}", json={"Labor_Category": "Τεχνίτης"})

    insert, update = audit_rows(db, "tbl_LaborResources", f"Employee_ID={employee_id}")
    assert (insert.Action, insert.Username) == ("INSERT", "test_admin")
    assert json.loads(update.Changes_JSON) == {"Labor_Category": ["Χειριστής ZZT", "Τεχνίτης"]}
