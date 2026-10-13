import json
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import AuditLog, Item

# Κωδικοί με «ZZT» ώστε να μη συγκρούονται με πραγματικά είδη της βάσης
ITEM = {
    "Item_Code": "30ZZT001",
    "Item_Name": "Δοκιμαστική καρέκλα ZZT",
    "Item_Category_Prefix": "30",
    "BSSG_Code": "02",
    "Pillar_Code": "02-3",
    "Group_Code": "02-3-001",
    "Base_Material_Code": "01",
    "Weight_kg": "2.35",
    "Is_Produced": True,
}


def audit_rows(db, table: str, key: str) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).where(AuditLog.Table_Name == table, AuditLog.Record_Key == key)
                           .order_by(AuditLog.Audit_ID)))


def create(client, **overrides) -> dict:
    response = client.post("/api/items", json={**ITEM, **overrides})
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.fixture
def expert(make_user, login):
    make_user("test_expert", "EXPERT", modules={"ITEMS": True})
    return login("test_expert")


# --- δημιουργία ---

def test_create_item_is_201(expert, db):
    body = create(expert)

    assert (body["Item_Code"], body["Is_Active"], body["UoM"]) == ("30ZZT001", True, "τεμ.")
    assert Decimal(body["Weight_kg"]) == Decimal("2.35")
    assert body["logistics_units"] == []
    assert db.get(Item, body["Item_ID"]).Created_By == "test_expert"


def test_duplicate_code_is_409(admin):
    create(admin)
    response = admin.post("/api/items", json=ITEM)
    assert response.status_code == 409
    assert response.json()["message"] == "Ο κωδικός 30ZZT001 υπάρχει ήδη"


@pytest.mark.parametrize("patch", [
    {"Item_Code": "31ZZT001"},                                  # δεν ξεκινά με το prefix
    {"Item_Category_Prefix": "77", "Item_Code": "77ZZT001"},    # άγνωστο prefix
    {"Item_Category_Prefix": "12", "Item_Code": "12699ZZT1"},   # ανήκει στο πιο ειδικό prefix 12699
])
def test_wrong_prefix_is_422(admin, patch):
    assert admin.post("/api/items", json={**ITEM, **patch}).status_code == 422


@pytest.mark.parametrize("patch", [
    {"Pillar_Code": "01-1"},                         # η ομάδα 02-3-001 δεν ανήκει στον πυλώνα 01-1
    {"BSSG_Code": "01"},                             # ο πυλώνας 02-3 δεν ανήκει στο BSSG 01
    {"Pillar_Code": None, "BSSG_Code": "04"},        # ούτε μέσω της ομάδας
])
def test_inconsistent_hierarchy_is_422(admin, patch):
    assert admin.post("/api/items", json={**ITEM, **patch}).status_code == 422


@pytest.mark.parametrize("patch", [
    {"Customer_ID": 999999999}, {"Base_Material_Code": "ZZ"}, {"Fason_Base_Item_ID": 999999999}, {"Group_Code": "nope"},
])
def test_unknown_reference_is_422_with_a_clear_message(admin, patch):
    response = admin.post("/api/items", json={**ITEM, **patch})
    assert response.status_code == 422
    assert "δεν υπάρχει" in response.json()["message"]


# --- αλλαγή ---

def test_patch_changes_only_the_sent_field(admin):
    created = create(admin)

    response = admin.patch(f"/api/items/{created['Item_ID']}", json={"Notes": "νέα σημείωση"})

    assert response.status_code == 200
    updated = response.json()["data"]
    assert updated["Notes"] == "νέα σημείωση"
    assert updated["Updated_By"] == "test_admin"
    # το Weight_kg συγκρίνεται ως αριθμός: η βάση γράφει 2.35000, εμείς στείλαμε 2.35
    unchanged = set(created) - {"Notes", "Updated_At", "Updated_By", "Weight_kg"}
    assert {k: updated[k] for k in unchanged} == {k: created[k] for k in unchanged}
    assert Decimal(updated["Weight_kg"]) == Decimal(created["Weight_kg"])


def test_patch_can_clear_an_optional_field_but_not_a_required_one(admin):
    item_id = create(admin)["Item_ID"]
    assert admin.patch(f"/api/items/{item_id}", json={"Weight_kg": None}).json()["data"]["Weight_kg"] is None
    assert admin.patch(f"/api/items/{item_id}", json={"Item_Name": None}).status_code == 422


def test_patch_is_validated_against_the_whole_item(admin):
    first = create(admin)
    second = create(admin, Item_Code="30ZZT002")
    url = f"/api/items/{second['Item_ID']}"

    assert admin.patch(url, json={"Item_Code": "30ZZT001"}).status_code == 409
    assert admin.patch(url, json={"Item_Code": "31ZZT002"}).status_code == 422       # το prefix έμεινε 30
    assert admin.patch(url, json={"Group_Code": "01-1-100"}).status_code == 422      # ο πυλώνας έμεινε 02-3
    assert admin.patch(url, json={"Fason_Base_Item_ID": second["Item_ID"]}).status_code == 422
    assert admin.patch(url, json={"Fason_Base_Item_ID": first["Item_ID"]}).status_code == 200


def test_code_change_is_allowed_and_audited(admin, db):
    item_id = create(admin)["Item_ID"]

    assert admin.patch(f"/api/items/{item_id}", json={"Item_Code": "30ZZT999"}).status_code == 200

    row = audit_rows(db, "tbl_Items", f"Item_ID={item_id}")[-1]
    assert json.loads(row.Changes_JSON) == {"Item_Code": ["30ZZT001", "30ZZT999"]}


def test_unknown_item_is_404(admin):
    assert admin.get("/api/items/999999999").status_code == 404
    assert admin.patch("/api/items/999999999", json={"Notes": "x"}).status_code == 404
    assert admin.post("/api/items/999999999/deactivate").status_code == 404


# --- ενεργό / ανενεργό ---

def test_deactivated_item_leaves_the_default_list(admin):
    item_id = create(admin)["Item_ID"]

    assert admin.post(f"/api/items/{item_id}/deactivate").json()["data"]["Is_Active"] is False

    def codes(**params):
        items = admin.get("/api/items", params={"q": "ZZT", **params}).json()["data"]["items"]
        return [i["Item_Code"] for i in items]
    assert codes() == []
    assert codes(is_active="false") == ["30ZZT001"]

    assert admin.post(f"/api/items/{item_id}/activate").json()["data"]["Is_Active"] is True
    assert codes() == ["30ZZT001"]


# --- λίστα ---

def test_q_filter_and_pagination(admin):
    for n in (3, 1, 2):
        create(admin, Item_Code=f"30ZZT00{n}")
    create(admin, Item_Code="30QQQ001", Item_Name="Άσχετο")

    page1 = admin.get("/api/items", params={"q": "ZZT", "page_size": 2}).json()["data"]
    page2 = admin.get("/api/items", params={"q": "ZZT", "page_size": 2, "page": 2}).json()["data"]

    assert (page1["total"], page1["page"], page1["page_size"]) == (3, 1, 2)
    assert [i["Item_Code"] for i in page1["items"]] == ["30ZZT001", "30ZZT002"]
    assert [i["Item_Code"] for i in page2["items"]] == ["30ZZT003"]
    assert "Notes" not in page1["items"][0]            # το ItemListOut έχει λιγότερα πεδία


def test_list_filters(admin):
    create(admin)
    create(admin, Item_Code="10ZZT001", Item_Name="Δοκιμαστική πρώτη ύλη", Item_Category_Prefix="10",
           Is_Produced=False, Is_Purchased=True,
           BSSG_Code=None, Pillar_Code=None, Group_Code=None)

    def codes(**params):
        items = admin.get("/api/items", params={"q": "ZZT", **params}).json()["data"]["items"]
        return [i["Item_Code"] for i in items]
    assert codes() == ["10ZZT001", "30ZZT001"]
    assert codes(prefix="10") == ["10ZZT001"]
    assert codes(is_purchased="true") == ["10ZZT001"]
    assert codes(is_produced="true") == ["30ZZT001"]
    assert codes(group_code="02-3-001") == ["30ZZT001"]
    assert codes(bssg_code="02") == ["30ZZT001"]
    assert admin.get("/api/items", params={"q": "καρέκλα ZZT"}).json()["data"]["total"] == 1      # το q ψάχνει και στο όνομα


# --- δικαιώματα ---

def test_user_without_items_permission_gets_403(user):
    assert user.post("/api/items", json=ITEM).status_code == 403


def test_only_admin_or_expert_with_can_edit_writes(make_user, login):
    make_user("test_u", "USER", modules={"ITEMS": True})
    make_user("test_ro", "EXPERT", modules={"ITEMS": False})
    make_user("test_other", "EXPERT", modules={"BOM": True})
    for username in ("test_u", "test_ro", "test_other"):
        c = login(username)
        assert c.post("/api/items", json=ITEM).status_code == 403
        assert c.get("/api/items").status_code == 200      # η ανάγνωση είναι για όλους


def test_anonymous_gets_401(client):
    assert client.get("/api/items").status_code == 401
    assert client.post("/api/items", json=ITEM).status_code == 401


# --- audit ---

def test_create_and_update_are_audited(admin, db):
    item_id = create(admin)["Item_ID"]
    admin.patch(f"/api/items/{item_id}", json={"Item_Name": "Άλλο όνομα", "Weight_kg": "2.35"})
    admin.post(f"/api/items/{item_id}/deactivate")

    insert, update, deactivate = audit_rows(db, "tbl_Items", f"Item_ID={item_id}")
    assert (insert.Action, insert.Username) == ("INSERT", "test_admin")
    assert json.loads(insert.Changes_JSON)["Item_Code"] == [None, "30ZZT001"]
    assert update.Action == "UPDATE"
    # το Weight_kg στάλθηκε αλλά δεν άλλαξε → δεν γράφεται
    assert json.loads(update.Changes_JSON) == {"Item_Name": ["Δοκιμαστική καρέκλα ZZT", "Άλλο όνομα"]}
    assert json.loads(deactivate.Changes_JSON) == {"Is_Active": [True, False]}


# --- logistics units ---

BOX = {"LU_Level": 1, "Description": "Κιβώτιο", "Base_Units_Per_LU": "12",
       "Length_m": "1.2", "Width_m": "0.8", "Height_m": "1.0"}
PALLET = {"LU_Level": 3, "Description": "Παλέτα", "Base_Units_Per_LU": "240"}


def test_logistics_units_return_the_computed_volume(admin):
    item_id = create(admin)["Item_ID"]

    response = admin.put(f"/api/items/{item_id}/logistics-units", json=[PALLET, BOX])

    assert response.status_code == 200
    box, pallet = response.json()["data"]["logistics_units"]      # ταξινομημένα κατά LU_Level
    assert Decimal(box["Volume_m3"]) == Decimal("0.96")
    assert pallet["Volume_m3"] is None                            # χωρίς διαστάσεις δεν υπάρχει όγκος
    fetched = admin.get(f"/api/items/{item_id}").json()["data"]["logistics_units"]
    assert [lu["LU_Level"] for lu in fetched] == [1, 3]


def test_put_replaces_the_whole_list_and_is_audited(admin, db):
    item_id = create(admin)["Item_ID"]
    url = f"/api/items/{item_id}/logistics-units"
    admin.put(url, json=[BOX, PALLET])

    units = admin.put(url, json=[{**BOX, "Height_m": "0.5"}]).json()["data"]["logistics_units"]

    assert [lu["LU_Level"] for lu in units] == [1]
    assert Decimal(units[0]["Volume_m3"]) == Decimal("0.48")
    changes = json.loads(audit_rows(db, "tbl_LogisticsUnits", f"Item_ID={item_id}")[-1].Changes_JSON)
    assert set(changes) == {"LU1", "LU3"}
    assert changes["LU3"][1] is None                              # η παλέτα σβήστηκε
    assert admin.put(url, json=[]).json()["data"]["logistics_units"] == []


@pytest.mark.parametrize("units", [
    [BOX, {**PALLET, "LU_Level": 1}],              # ίδιο επίπεδο δύο φορές
    [{**BOX, "Base_Units_Per_LU": "0"}],           # πρέπει > 0
    [{**BOX, "LU_Level": 4}],                      # η βάση δέχεται 1–3
])
def test_invalid_logistics_units_are_422(admin, units):
    item_id = create(admin)["Item_ID"]
    assert admin.put(f"/api/items/{item_id}/logistics-units", json=units).status_code == 422
