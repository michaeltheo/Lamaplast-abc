import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from conftest import audit_rows
from sqlalchemy import func, select

from app.models import MouldRunMaterial


@pytest.fixture
def ids(admin, make_item) -> SimpleNamespace:
    """Τρία καλούπια (ένα ανά τύπο), δύο είδη εξόδου και δύο υλικά."""
    def mould(code: str, mould_type: str, cavities: int) -> int:
        body = {"Mould_Code": code, "Mould_Name": code, "Mould_Type": mould_type, "Cavities": cavities}
        response = admin.post("/api/moulds", json=body)
        assert response.status_code == 201, response.text
        return response.json()["data"]["Mould_ID"]

    return SimpleNamespace(
        single=mould("ZZT-K1", "SINGLE", 1),
        multi=mould("ZZT-K4", "MULTI_CAVITY", 4),
        family=mould("ZZT-KF", "FAMILY", 4),
        seat=make_item("30ZZT101", "30").Item_ID,
        back=make_item("30ZZT102", "30").Item_ID,
        resin=make_item("10ZZT001", "10", Is_Purchased=True).Item_ID,
        masterbatch=make_item("12699ZZT1", "12699").Item_ID,
    )


def output(item_id: int, pieces: int = 1, share: str | None = None) -> dict:
    return {"Item_ID": item_id, "Pieces_Per_Cycle": pieces, "Net_Part_Weight_g": "850.5", "Cost_Share_Pct": share}


def mix(ids, resin: str = "0.98", masterbatch: str = "0.02") -> list[dict]:
    return [{"Material_Item_ID": ids.resin, "Mix_Pct": resin, "Is_Regrind_Source": True},
            {"Material_Item_ID": ids.masterbatch, "Material_Type": "MASTERBATCH", "Mix_Pct": masterbatch,
             "Sequence": 20}]


def run(ids, **overrides) -> dict:
    return {"MouldRun_Code": "ZZT-MR-1", "Mould_ID": ids.single, "Machine_Category": "M3",
            "Cycles_Per_Hour": "120", "Setup_Min": "45", "Avg_Batch_Qty": "5000",
            "outputs": [output(ids.seat)], "materials": mix(ids), **overrides}


def create(client, body: dict) -> dict:
    response = client.post("/api/mould-runs", json=body)
    assert response.status_code == 201, response.text
    return response.json()["data"]


# --- δημιουργία ---

def test_create_run_with_outputs_and_materials(admin, ids):
    body = create(admin, run(ids))

    assert Decimal(body["Sec_Per_Cycle"]) == Decimal(30)                       # 3600 / 120 κύκλους την ώρα
    assert (Decimal(body["Scrap_Pct"]), Decimal(body["Operator_Load_Factor"])) == (Decimal("0.041"), Decimal(1))
    assert [(o["Item_ID"], o["Pieces_Per_Cycle"]) for o in body["outputs"]] == [(ids.seat, 1)]
    assert [m["Material_Item_ID"] for m in body["materials"]] == [ids.resin, ids.masterbatch]   # κατά Sequence
    assert [m["Material_Type"] for m in body["materials"]] == ["BASE_RESIN", "MASTERBATCH"]
    fetched = admin.get(f"/api/mould-runs/{body['MouldRun_ID']}").json()["data"]
    assert (fetched["MouldRun_Code"], len(fetched["outputs"]), len(fetched["materials"])) == ("ZZT-MR-1", 1, 2)


def test_duplicate_code_or_mould_and_category_is_409(admin, ids):
    create(admin, run(ids))
    assert admin.post("/api/mould-runs", json=run(ids, Mould_ID=ids.multi)).status_code == 409
    same_pair = admin.post("/api/mould-runs", json=run(ids, MouldRun_Code="ZZT-MR-2"))
    assert same_pair.status_code == 409
    assert same_pair.json()["message"] == "Το καλούπι ZZT-K1 έχει ήδη run στην κατηγορία M3"
    create(admin, run(ids, MouldRun_Code="ZZT-MR-2", Machine_Category="M4"))     # άλλη κατηγορία: επιτρέπεται


# --- υλικά: άθροισμα Mix_Pct = 100% ---

@pytest.mark.parametrize(("masterbatch", "expected"), [
    ("0.0199", 422),      # 99,99%
    ("0.02", 201),        # 100%
    ("0.0201", 422),      # 100,01%
    ("0.01999", 201),     # 99,999%: μέσα στην ανοχή ±0.00001
    ("0.02001", 201),     # 100,001%: μέσα στην ανοχή
    ("0.01998", 422),     # 99,998%: έξω από την ανοχή
])
def test_mix_must_sum_to_100_percent(admin, ids, masterbatch, expected):
    response = admin.post("/api/mould-runs", json=run(ids, materials=mix(ids, masterbatch=masterbatch)))
    assert response.status_code == expected


def test_material_must_be_raw_material_or_purchased(admin, ids, make_item):
    not_material = [{"Material_Item_ID": ids.back, "Mix_Pct": "1"}]
    response = admin.post("/api/mould-runs", json=run(ids, materials=not_material))
    assert response.status_code == 422
    assert response.json()["message"] == "Το είδος 30ZZT102 δεν είναι πρώτη ύλη ούτε αγοραζόμενο"

    purchased = make_item("34ZZT001", "34", Is_Purchased=True).Item_ID          # αγοραζόμενο εξάρτημα: επιτρέπεται
    create(admin, run(ids, materials=[{"Material_Item_ID": purchased, "Mix_Pct": "1"}]))


# --- outputs ---

@pytest.mark.parametrize(("shares", "expected"), [
    ((None, None), 201),              # όλα κενά: το κόστος μοιράζεται κατά βάρος
    (("0.6", "0.4"), 201),            # 100%
    (("0.6", None), 422),             # μισά συμπληρωμένα
    (("0.6", "0.3999"), 422),         # 99,99%
    (("0.6", "0.4001"), 422),         # 100,01%
    (("0.6", "0.399999"), 201),       # μέσα στην ανοχή ±0.000001
])
def test_cost_shares_are_all_empty_or_sum_to_100_percent(admin, ids, shares, expected):
    outputs = [output(ids.seat, 2, shares[0]), output(ids.back, 2, shares[1])]
    response = admin.post("/api/mould-runs", json=run(ids, Mould_ID=ids.family, outputs=outputs))
    assert response.status_code == expected


def test_outputs_must_fit_the_mould_type(admin, ids):
    codes = iter(range(100))

    def status(mould_id: int, *outputs: dict) -> int:
        body = run(ids, MouldRun_Code=f"ZZT-MR-{next(codes)}", Mould_ID=mould_id, outputs=list(outputs))
        return admin.post("/api/mould-runs", json=body).status_code

    # SINGLE: ακριβώς ένα είδος, ένα τεμάχιο
    assert status(ids.single, output(ids.seat, 2)) == 422
    assert status(ids.single, output(ids.seat), output(ids.back)) == 422
    # MULTI_CAVITY (4 κοιλότητες): ένα είδος, έως 4 τεμάχια
    assert status(ids.multi, output(ids.seat, 5)) == 422
    assert status(ids.multi, output(ids.seat, 2), output(ids.back, 2)) == 422
    assert status(ids.multi, output(ids.seat, 4)) == 201
    # FAMILY (4 κοιλότητες): πολλά είδη, συνολικά έως 4 τεμάχια
    assert status(ids.family, output(ids.seat, 2), output(ids.back, 3)) == 422
    assert status(ids.family, output(ids.seat, 2), output(ids.seat, 2)) == 422       # το ίδιο είδος δύο φορές
    assert status(ids.family, output(ids.seat, 1), output(ids.back, 3)) == 201


# --- το run ---

@pytest.mark.parametrize("patch", [
    {"Cycles_Per_Hour": "0"}, {"Scrap_Pct": "1.5"}, {"Scrap_Pct": "-0.1"}, {"Operator_Load_Factor": "0.7"},
    {"Machine_Category": "ZZ"}, {"Mould_ID": 999999999}, {"Avg_Batch_Qty": "0"},
    {"outputs": []}, {"materials": []},
    {"outputs": [{"Item_ID": 1, "Pieces_Per_Cycle": 0, "Net_Part_Weight_g": "10"}]},
    {"outputs": [{"Item_ID": 1, "Pieces_Per_Cycle": 1, "Net_Part_Weight_g": "0"}]},
    {"outputs": [{"Item_ID": 999999999, "Pieces_Per_Cycle": 1, "Net_Part_Weight_g": "10"}]},
])
def test_invalid_run_is_422(admin, ids, patch):
    assert admin.post("/api/mould-runs", json=run(ids, **patch)).status_code == 422


@pytest.mark.parametrize("load", ["0.33", "0.5", "1.0", "2.0"])
def test_operator_load_accepts_only_the_enum_values(admin, ids, load):
    assert Decimal(create(admin, run(ids, Operator_Load_Factor=load))["Operator_Load_Factor"]) == Decimal(load)


# --- PUT: αντικαθιστά run και παιδιά μαζί ---

def test_put_replaces_run_outputs_and_materials_in_one_go(admin, ids, db):
    created = create(admin, run(ids))
    run_id = created["MouldRun_ID"]
    only_resin = [{"Material_Item_ID": ids.resin, "Mix_Pct": "1"}]

    response = admin.put(f"/api/mould-runs/{run_id}", json=run(ids, Cycles_Per_Hour="150", materials=only_resin,
                                                              outputs=[output(ids.back)]))

    assert response.status_code == 200
    body = response.json()["data"]
    assert Decimal(body["Sec_Per_Cycle"]) == Decimal(24)
    assert [o["Item_ID"] for o in body["outputs"]] == [ids.back]
    assert [(m["Material_Item_ID"], Decimal(m["Mix_Pct"])) for m in body["materials"]] == [(ids.resin, Decimal(1))]
    stored = db.scalar(select(func.count()).select_from(MouldRunMaterial).where(MouldRunMaterial.MouldRun_ID == run_id))
    assert stored == 1                                                           # το masterbatch σβήστηκε

    insert, update = audit_rows(db, "tbl_MouldRuns", f"MouldRun_ID={run_id}")
    assert set(json.loads(insert.Changes_JSON)) >= {"MouldRun_Code", "outputs", "materials"}
    changes = json.loads(update.Changes_JSON)
    assert {"Cycles_Per_Hour", "outputs", "materials"} <= set(changes)
    assert set(changes["materials"][0]) == {str(ids.resin), str(ids.masterbatch)}
    assert set(changes["materials"][1]) == {str(ids.resin)}


def test_a_rejected_put_changes_nothing(admin, ids):
    created = create(admin, run(ids))
    url = f"/api/mould-runs/{created['MouldRun_ID']}"

    bad = run(ids, Cycles_Per_Hour="999", materials=mix(ids, masterbatch="0.5"))
    assert admin.put(url, json=bad).status_code == 422
    assert admin.get(url).json()["data"] == created
    assert admin.put("/api/mould-runs/999999999", json=run(ids)).status_code == 404


# --- λίστα ---

def test_list_by_item_returns_every_run_that_produces_it(admin, ids):
    create(admin, run(ids))
    create(admin, run(ids, MouldRun_Code="ZZT-MR-2", Mould_ID=ids.family,
                      outputs=[output(ids.seat, 2), output(ids.back, 2)]))
    off = create(admin, run(ids, MouldRun_Code="ZZT-MR-3", Mould_ID=ids.multi, outputs=[output(ids.back, 4)]))
    admin.post(f"/api/mould-runs/{off['MouldRun_ID']}/deactivate")

    def codes(**params):
        data = admin.get("/api/mould-runs", params={"q": "ZZT", **params}).json()["data"]
        assert data["total"] == len(data["items"])
        return [r["MouldRun_Code"] for r in data["items"]]
    assert codes(item_id=ids.seat) == ["ZZT-MR-1", "ZZT-MR-2"]
    assert codes(item_id=ids.back) == ["ZZT-MR-2"]
    assert codes(item_id=ids.back, is_active="false") == ["ZZT-MR-3"]
    assert codes(mould_id=ids.family, machine_category="M3") == ["ZZT-MR-2"]
    listed = admin.get("/api/mould-runs", params={"item_id": ids.back}).json()["data"]["items"][0]
    assert len(listed["outputs"]) == 2 and len(listed["materials"]) == 2          # η λίστα φέρνει και τα παιδιά


# --- δικαιώματα ---

def test_only_the_moulds_module_can_write(user, ids, make_user, login):
    assert user.post("/api/mould-runs", json=run(ids)).status_code == 403
    assert user.get("/api/mould-runs").status_code == 200
    make_user("test_expert", "EXPERT", modules={"MOULDS": True})
    create(login("test_expert"), run(ids))


def test_anonymous_gets_401(client):
    assert client.get("/api/mould-runs").status_code == 401
