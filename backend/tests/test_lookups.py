import pytest
from app.core.db import SessionLocal, get_db
from app.main import app
from app.models import CommercialPillar
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def db():
    """Session που δεν κάνει ποτέ commit: ό,τι αλλάξει το test χάνεται στο τέλος."""
    session = SessionLocal()
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.rollback()
        session.close()


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
def test_lookup_returns_all_seeded_rows(path, expected):
    response = client.get(f"/api/lookups/{path}")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == expected
    assert len(body["items"]) == expected


def test_pillars_filtered_by_bssg_are_only_furniture():
    pillars = client.get("/api/lookups/pillars", params={"bssg": "02"}).json()["items"]
    assert [p["Pillar_Code"] for p in pillars] == ["02-1", "02-2", "02-3", "02-4", "02-5"]
    assert {p["BSSG_Code"] for p in pillars} == {"02"}


def test_product_groups_filtered_by_pillar():
    groups = client.get("/api/lookups/product-groups", params={"pillar": "01-2"}).json()["items"]
    assert len(groups) == 7
    assert {g["Pillar_Code"] for g in groups} == {"01-2"}


def test_machine_categories_filtered_by_group():
    categories = client.get("/api/lookups/machine-categories", params={"group": "INJECTION"}).json()["items"]
    assert [c["Category_Code"] for c in categories] == ["M1", "M2", "M3", "M4", "M5", "M6"]


def test_lookups_accept_page_and_page_size():
    body = client.get("/api/lookups/product-groups", params={"page": 2, "page_size": 10}).json()
    assert (body["page"], body["page_size"], body["total"]) == (2, 10, 39)
    assert body["items"][0]["Group_Code"] == "01-2-201"


def test_bssg_is_ordered_by_sort_order():
    codes = [b["BSSG_Code"] for b in client.get("/api/lookups/bssg").json()["items"]]
    assert codes == ["01", "02", "03", "04", "99"]


def test_inactive_rows_are_hidden_unless_active_only_is_false(db):
    db.get(CommercialPillar, "02-5").Is_Active = False
    db.flush()

    active = client.get("/api/lookups/pillars", params={"bssg": "02"}).json()["items"]
    everything = client.get("/api/lookups/pillars", params={"bssg": "02", "active_only": "false"}).json()["items"]

    assert "02-5" not in [p["Pillar_Code"] for p in active]
    assert "02-5" in [p["Pillar_Code"] for p in everything]


def test_audit_columns_are_not_exposed():
    row = client.get("/api/lookups/bssg").json()["items"][0]
    assert set(row) == {"BSSG_Code", "BSSG_Name", "Sort_order", "Is_Active"}
