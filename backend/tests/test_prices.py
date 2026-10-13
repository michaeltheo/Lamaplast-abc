import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from conftest import audit_rows
from sqlalchemy import select

from app.models import Customer


@pytest.fixture
def ids(db, make_item, make_scenario) -> SimpleNamespace:
    def customer(code: str) -> int:
        return db.scalar(select(Customer.Customer_ID).where(Customer.Customer_Code == code))

    return SimpleNamespace(
        item=make_item("10ZZT001", "10", Is_Purchased=True).Item_ID,
        other_item=make_item("10ZZT002", "10", Is_Purchased=True).Item_ID,
        scenario=make_scenario().Scenario_ID,
        locked=make_scenario("ZZT κλειδωμένο", locked=True).Scenario_ID,
        customer=customer("000"),
        other_customer=customer("999"),
    )


def price(ids, valid_from: str = "2025-01-01", **overrides) -> dict:
    return {"Item_ID": ids.item, "Scenario_ID": ids.scenario, "Valid_From": valid_from, "Price_EUR": "1.45",
            **overrides}


def post(client, url: str, body: dict) -> dict:
    response = client.post(url, json=body)
    assert response.status_code == 201, response.text
    return response.json()["data"]


# ====================== τιμές αγοράς ======================

def test_create_price_is_201_with_eur_defaults(admin, ids):
    body = post(admin, "/api/prices", price(ids, Supplier="Προμηθευτής ZZT"))

    assert (body["Currency"], Decimal(body["FX_Rate"]), body["Source"]) == ("EUR", 1, "MANUAL")
    assert (body["Valid_From"], body["Valid_To"], body["Price_Local"]) == ("2025-01-01", None, None)
    assert body["Created_By"] == "test_admin"


def test_a_newer_price_closes_the_open_one_the_day_before(admin, ids, db):
    first = post(admin, "/api/prices", price(ids))

    second = post(admin, "/api/prices", price(ids, "2025-07-01", Price_EUR="1.52", Reason="Αύξηση προμηθευτή"))

    assert admin.get(f"/api/prices/{first['Price_ID']}").json()["data"]["Valid_To"] == "2025-06-30"
    assert second["Valid_To"] is None
    insert, closed = audit_rows(db, "tbl_Prices", f"Price_ID={first['Price_ID']}")
    assert insert.Action == "INSERT"
    assert json.loads(closed.Changes_JSON) == {"Valid_To": [None, "2025-06-30"]}


def test_overlapping_periods_are_422(admin, ids):
    post(admin, "/api/prices", price(ids))                                    # 2025-01-01 → ανοιχτή

    def status(valid_from: str, valid_to: str | None = None) -> int:
        return admin.post("/api/prices", json=price(ids, valid_from, Valid_To=valid_to)).status_code
    assert status("2025-01-01") == 422                                        # ίδια έναρξη
    assert status("2024-06-01") == 422                                        # ανοιχτή που ξεκινά νωρίτερα
    assert status("2024-06-01", "2025-01-01") == 422                          # ακουμπά την πρώτη μέρα
    assert status("2025-02-01", "2025-01-15") == 422                          # λήξη πριν την έναρξη
    assert status("2024-06-01", "2024-12-31") == 201                          # ακριβώς πριν: επιτρέπεται

    response = admin.post("/api/prices", json=price(ids, "2024-01-01"))
    assert response.json()["message"] == "Το διάστημα επικαλύπτει την τιμή που ισχύει από 01/06/2024 έως 31/12/2024"
    # άλλο είδος ή άλλο σενάριο: ξεχωριστό ιστορικό
    assert admin.post("/api/prices", json=price(ids, Item_ID=ids.other_item)).status_code == 201


def test_current_price_on_a_date(admin, ids):
    post(admin, "/api/prices", price(ids))
    post(admin, "/api/prices", price(ids, "2025-07-01", Price_EUR="1.52"))
    params = {"item_id": ids.item, "scenario_id": ids.scenario}

    def on(day: str | None):
        return admin.get("/api/prices/current", params={**params, "on": day} if day else params)
    assert Decimal(on("2025-03-15").json()["data"]["Price_EUR"]) == Decimal("1.45")
    assert Decimal(on("2025-06-30").json()["data"]["Price_EUR"]) == Decimal("1.45")
    assert Decimal(on("2025-07-01").json()["data"]["Price_EUR"]) == Decimal("1.52")
    assert Decimal(on(None).json()["data"]["Price_EUR"]) == Decimal("1.52")       # χωρίς on: σήμερα
    assert on("2024-12-31").status_code == 404
    assert on("not-a-date").status_code == 422


def test_patch_touches_only_reason_supplier_and_valid_to(admin, ids):
    first = post(admin, "/api/prices", price(ids))
    post(admin, "/api/prices", price(ids, "2025-07-01"))
    url = f"/api/prices/{first['Price_ID']}"

    assert admin.patch(url, json={"Price_EUR": "9.99"}).status_code == 422       # νέα τιμή = νέα γραμμή
    assert admin.patch(url, json={"Valid_From": "2024-01-01"}).status_code == 422
    patched = admin.patch(url, json={"Reason": "διόρθωση", "Supplier": "Άλλος"}).json()["data"]
    assert (patched["Reason"], patched["Supplier"], patched["Valid_To"]) == ("διόρθωση", "Άλλος", "2025-06-30")

    assert admin.patch(url, json={"Valid_To": "2025-03-31"}).status_code == 200  # κλείνει νωρίτερα: αφήνει κενό
    assert admin.patch(url, json={"Valid_To": "2024-12-31"}).status_code == 422  # πριν από το Valid_From
    assert admin.patch(url, json={"Valid_To": "2025-07-01"}).status_code == 422  # πέφτει πάνω στην επόμενη
    assert admin.patch(url, json={"Valid_To": None}).status_code == 422          # ανοιχτή = επικάλυψη
    assert admin.patch("/api/prices/999999999", json={"Reason": "x"}).status_code == 404


def test_foreign_currency_needs_fx_rate_and_local_price(admin, ids):
    def usd(**fields):
        body = {k: v for k, v in price(ids, Currency="usd", **fields).items() if v is not None}
        return admin.post("/api/prices", json=body)

    assert usd().status_code == 422                                              # λείπουν FX_Rate και Price_Local
    assert usd(Price_Local="110").status_code == 422                             # λείπει το FX_Rate
    assert usd(FX_Rate="1.1").status_code == 422                                 # λείπει το Price_Local
    mismatch = usd(Price_Local="110", FX_Rate="1.1", Price_EUR="105")
    assert mismatch.status_code == 422
    assert "Price_Local / FX_Rate = 100.00000" in mismatch.json()["message"]

    body = usd(Price_Local="110", FX_Rate="1.1", Price_EUR="100.05").json()["data"]   # μέσα στο 0,1%
    assert (body["Currency"], Decimal(body["Price_EUR"])) == ("USD", Decimal("100.05"))


def test_price_eur_is_computed_when_missing_in_foreign_currency(admin, ids):
    body = {**price(ids, Currency="USD", Price_Local="110", FX_Rate="1.1"), "Price_EUR": None}
    assert Decimal(post(admin, "/api/prices", body)["Price_EUR"]) == Decimal(100)        # 110 / 1,1


@pytest.mark.parametrize("patch", [
    {"FX_Rate": "1.2"},                 # EUR με ισοτιμία ≠ 1
    {"Price_Local": "2"},               # EUR με τοπική τιμή ≠ Price_EUR
    {"Price_EUR": None},                # EUR χωρίς τιμή
    {"Price_EUR": "-1"}, {"Source": "GUESS"}, {"Currency": "EURO"}, {"Item_ID": 999999999},
])
def test_invalid_price_is_422(admin, ids, patch):
    assert admin.post("/api/prices", json=price(ids, **patch)).status_code == 422


def test_locked_or_unknown_scenario(admin, ids, db):
    response = admin.post("/api/prices", json=price(ids, Scenario_ID=ids.locked))
    assert response.status_code == 422
    assert "κλειδωμένο" in response.json()["message"]
    assert admin.post("/api/prices", json=price(ids, Scenario_ID=999999999)).status_code == 404


def test_list_is_filtered_by_item_scenario_and_date(admin, ids):
    post(admin, "/api/prices", price(ids))
    post(admin, "/api/prices", price(ids, "2025-07-01", Price_EUR="1.52"))
    post(admin, "/api/prices", price(ids, Item_ID=ids.other_item, Price_EUR="2"))

    def prices(**params):
        data = admin.get("/api/prices", params={"scenario_id": ids.scenario, **params}).json()["data"]
        return [(p["Item_ID"], p["Valid_From"]) for p in data["items"]]
    assert prices() == [(ids.item, "2025-07-01"), (ids.item, "2025-01-01"), (ids.other_item, "2025-01-01")]
    assert prices(item_id=ids.other_item) == [(ids.other_item, "2025-01-01")]
    assert prices(on="2025-03-01") == [(ids.item, "2025-01-01"), (ids.other_item, "2025-01-01")]


def test_only_the_prices_module_can_write(user, ids, make_user, login):
    assert user.post("/api/prices", json=price(ids)).status_code == 403
    assert user.get("/api/prices").status_code == 200
    make_user("test_expert", "EXPERT", modules={"PRICES": True})
    post(login("test_expert"), "/api/prices", price(ids))


# ====================== τιμές πώλησης ======================

def sale(ids, valid_from: str = "2025-01-01", **overrides) -> dict:
    return {"Item_ID": ids.item, "Scenario_ID": ids.scenario, "Valid_From": valid_from, "Price_EUR": "10",
            **overrides}


def test_each_customer_has_its_own_price_history(admin, ids):
    generic = post(admin, "/api/sales-prices", sale(ids))
    special = post(admin, "/api/sales-prices", sale(ids, Customer_ID=ids.customer, Price_EUR="9"))

    post(admin, "/api/sales-prices", sale(ids, "2025-07-01", Customer_ID=ids.customer, Price_EUR="9.5"))

    # έκλεισε μόνο η τιμή του ίδιου πελάτη· η γενική έμεινε ανοιχτή
    assert admin.get(f"/api/sales-prices/{special['Sales_Price_ID']}").json()["data"]["Valid_To"] == "2025-06-30"
    assert admin.get(f"/api/sales-prices/{generic['Sales_Price_ID']}").json()["data"]["Valid_To"] is None
    assert admin.post("/api/sales-prices", json=sale(ids)).status_code == 422                  # γενική: επικάλυψη
    assert admin.post("/api/sales-prices", json=sale(ids, Customer_ID=999999999)).status_code == 422


def test_current_sales_price_falls_back_to_the_generic_one(admin, ids):
    post(admin, "/api/sales-prices", sale(ids))
    post(admin, "/api/sales-prices", sale(ids, Customer_ID=ids.customer, Price_EUR="9"))
    params = {"item_id": ids.item, "scenario_id": ids.scenario, "on": "2025-03-01"}

    def current(**extra):
        return admin.get("/api/sales-prices/current", params={**params, **extra})
    assert Decimal(current(customer_id=ids.customer).json()["data"]["Price_EUR"]) == Decimal(9)
    assert Decimal(current(customer_id=ids.other_customer).json()["data"]["Price_EUR"]) == Decimal(10)
    assert Decimal(current().json()["data"]["Price_EUR"]) == Decimal(10)
    assert current(on="2024-01-01").status_code == 404


def test_sales_price_patch_and_permissions(admin, user, ids, db):
    created = post(admin, "/api/sales-prices", sale(ids))
    url = f"/api/sales-prices/{created['Sales_Price_ID']}"

    assert admin.patch(url, json={"Price_EUR": "11"}).status_code == 422
    assert admin.patch(url, json={"Supplier": "x"}).status_code == 422            # οι πωλήσεις δεν έχουν προμηθευτή
    assert admin.patch(url, json={"Valid_To": "2025-12-31", "Reason": "λήξη συμφωνίας"}).status_code == 200
    assert user.patch(url, json={"Reason": "x"}).status_code == 403
    assert user.post("/api/sales-prices", json=sale(ids, "2026-01-01")).status_code == 403
    assert admin.post("/api/sales-prices", json=sale(ids, Scenario_ID=ids.locked)).status_code == 422

    insert, update = audit_rows(db, "tbl_SalesPrices", f"Sales_Price_ID={created['Sales_Price_ID']}")
    assert insert.Action == "INSERT"
    assert json.loads(update.Changes_JSON) == {"Reason": [None, "λήξη συμφωνίας"], "Valid_To": [None, "2025-12-31"]}


# ====================== ετήσιοι όγκοι ======================

def put_volumes(client, scenario_id: int, volumes: dict[int, str]):
    body = [{"Item_ID": item_id, "Annual_Qty": qty} for item_id, qty in volumes.items()]
    return client.put("/api/item-volumes", params={"scenario_id": scenario_id}, json=body)


def test_put_upserts_volumes_per_item(admin, ids, db):
    assert put_volumes(admin, ids.scenario, {ids.item: "1000", ids.other_item: "250.5"}).status_code == 200

    response = put_volumes(admin, ids.scenario, {ids.item: "1200"})        # το other_item δεν αγγίζεται

    assert response.status_code == 200
    assert [v["Item_ID"] for v in response.json()["data"]] == [ids.item]
    listed = admin.get("/api/item-volumes", params={"scenario_id": ids.scenario}).json()["data"]
    assert listed["total"] == 2
    assert [(v["Item_ID"], Decimal(v["Annual_Qty"])) for v in listed["items"]] == [
        (ids.item, Decimal(1200)), (ids.other_item, Decimal("250.5"))]       # κατά κωδικό είδους

    first, second = audit_rows(db, "tbl_ItemVolumes", f"Scenario_ID={ids.scenario}")
    assert set(json.loads(first.Changes_JSON)) == {str(ids.item), str(ids.other_item)}
    changes = json.loads(second.Changes_JSON)
    assert set(changes) == {str(ids.item)}
    assert [c["Annual_Qty"] for c in changes[str(ids.item)]] == ["1000.00", "1200"]


def test_invalid_volumes(admin, user, ids):
    url, params = "/api/item-volumes", {"scenario_id": ids.scenario}
    assert admin.put(url, params=params, json=[{"Item_ID": ids.item, "Annual_Qty": "1"}] * 2).status_code == 422
    assert put_volumes(admin, ids.scenario, {ids.item: "-1"}).status_code == 422
    assert put_volumes(admin, ids.scenario, {999999999: "1"}).status_code == 422
    assert put_volumes(admin, ids.locked, {ids.item: "1"}).status_code == 422
    assert put_volumes(admin, 999999999, {ids.item: "1"}).status_code == 404
    assert put_volumes(user, ids.scenario, {ids.item: "1"}).status_code == 403
    assert admin.get(url).status_code == 422                                  # το scenario_id είναι υποχρεωτικό
    assert admin.get(url, params={"scenario_id": ids.locked}).json()["data"]["total"] == 0
