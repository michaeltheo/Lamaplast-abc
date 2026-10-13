import pytest
from app.models import CommercialPillar


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("item-code-rules", 13),
        ("base-materials", 20),
        ("bssg", 5),
        ("pillars", 16),
        ("product-groups", 39),
        ("machine-categories", 8),
        ("global-defaults", 10),
    ],
)
def test_lookup_returns_all_seeded_rows(user, path, expected):
    response = user.get(f"/api/lookups/{path}")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total"] == expected
    assert len(body["items"]) == expected


def test_pillars_filtered_by_bssg_are_only_furniture(user):
    pillars = user.get("/api/lookups/pillars", params={"bssg": "02"}).json()["data"]["items"]
    assert [p["Pillar_Code"] for p in pillars] == ["02-1", "02-2", "02-3", "02-4", "02-5"]
    assert {p["BSSG_Code"] for p in pillars} == {"02"}


def test_product_groups_filtered_by_pillar(user):
    groups = user.get("/api/lookups/product-groups", params={"pillar": "01-2"}).json()["data"]["items"]
    assert len(groups) == 7
    assert {g["Pillar_Code"] for g in groups} == {"01-2"}


def test_machine_categories_filtered_by_group(user):
    categories = user.get("/api/lookups/machine-categories", params={"group": "INJECTION"}).json()["data"]["items"]
    assert [c["Category_Code"] for c in categories] == ["M1", "M2", "M3", "M4", "M5", "M6"]


def test_lookups_accept_page_and_page_size(user):
    body = user.get("/api/lookups/product-groups", params={"page": 2, "page_size": 10}).json()["data"]
    assert (body["page"], body["page_size"], body["total"]) == (2, 10, 39)
    assert body["items"][0]["Group_Code"] == "01-2-201"


def test_bssg_is_ordered_by_sort_order(user):
    codes = [b["BSSG_Code"] for b in user.get("/api/lookups/bssg").json()["data"]["items"]]
    assert codes == ["01", "02", "03", "04", "99"]


def test_inactive_rows_are_hidden_unless_active_only_is_false(user, db):
    db.get(CommercialPillar, "02-5").Is_Active = False
    db.flush()

    active = user.get("/api/lookups/pillars", params={"bssg": "02"}).json()["data"]["items"]
    everything = user.get("/api/lookups/pillars", params={"bssg": "02", "active_only": "false"}).json()["data"]["items"]

    assert "02-5" not in [p["Pillar_Code"] for p in active]
    assert "02-5" in [p["Pillar_Code"] for p in everything]


def test_audit_columns_are_not_exposed(user):
    row = user.get("/api/lookups/bssg").json()["data"]["items"][0]
    assert set(row) == {"BSSG_Code", "BSSG_Name", "Sort_order", "Is_Active"}


def test_lookups_require_login(client):
    assert client.get("/api/lookups/bssg").status_code == 401
