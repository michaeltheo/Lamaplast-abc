import json

from conftest import audit_rows

CUSTOMER = {"Customer_Code": "ZZT01", "Customer_Name": "Δοκιμαστικός πελάτης ZZT", "Notes": "δοκιμή"}


def create(client, **overrides) -> dict:
    response = client.post("/api/customers", json={**CUSTOMER, **overrides})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_create_customer_is_201(admin):
    body = create(admin)
    assert (body["Customer_Code"], body["Is_Internal"], body["Is_Active"]) == ("ZZT01", False, True)
    assert body["Created_By"] == "test_admin"


def test_duplicate_code_is_409(admin):
    create(admin)
    response = admin.post("/api/customers", json=CUSTOMER)
    assert response.status_code == 409
    assert response.json()["message"] == "Ο κωδικός πελάτη ZZT01 υπάρχει ήδη"


def test_patch_to_an_existing_code_is_409(admin):
    create(admin)
    other = create(admin, Customer_Code="ZZT02")
    assert admin.patch(f"/api/customers/{other['Customer_ID']}", json={"Customer_Code": "ZZT01"}).status_code == 409
    assert admin.patch(f"/api/customers/{other['Customer_ID']}", json={"Customer_Name": None}).status_code == 422


def test_list_filters_q_is_internal_and_is_active(admin):
    create(admin)
    internal = create(admin, Customer_Code="ZZT02", Is_Internal=True)
    admin.post(f"/api/customers/{internal['Customer_ID']}/deactivate")

    def codes(**params):
        items = admin.get("/api/customers", params={"q": "ZZT", **params}).json()["data"]["items"]
        return [c["Customer_Code"] for c in items]
    assert codes() == ["ZZT01"]
    assert codes(is_active="false") == ["ZZT02"]
    assert codes(is_active="false", is_internal="true") == ["ZZT02"]
    assert codes(is_internal="true") == []
    assert codes(q="πελάτης ZZT") == ["ZZT01"]


def test_seeded_customers_are_listed_by_code(user):
    codes = [c["Customer_Code"] for c in user.get("/api/customers").json()["data"]["items"]]
    assert codes == sorted(codes)
    assert {"000", "999"} <= set(codes)


def test_user_without_items_permission_gets_403(user, make_user, login):
    assert user.post("/api/customers", json=CUSTOMER).status_code == 403
    make_user("test_expert", "EXPERT", modules={"ITEMS": True})
    assert login("test_expert").post("/api/customers", json=CUSTOMER).status_code == 201


def test_anonymous_gets_401(client):
    assert client.get("/api/customers").status_code == 401


def test_unknown_customer_is_404(admin):
    assert admin.get("/api/customers/999999999").status_code == 404


def test_create_and_update_are_audited(admin, db):
    customer_id = create(admin)["Customer_ID"]
    admin.patch(f"/api/customers/{customer_id}", json={"Customer_Name": "Άλλο όνομα"})

    insert, update = audit_rows(db, "tbl_Customers", f"Customer_ID={customer_id}")
    assert (insert.Action, insert.Username) == ("INSERT", "test_admin")
    assert json.loads(insert.Changes_JSON)["Customer_Code"] == [None, "ZZT01"]
    assert json.loads(update.Changes_JSON) == {"Customer_Name": ["Δοκιμαστικός πελάτης ZZT", "Άλλο όνομα"]}
