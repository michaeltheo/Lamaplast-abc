from datetime import timedelta

import pytest
from conftest import new_client
from sqlalchemy import select

from app.cli import create_admin
from app.core.audit import log_change
from app.core.security import utcnow
from app.models import AuditLog, User


def rows_for(db, username: str) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).where(AuditLog.Username == username).order_by(AuditLog.Audit_ID)))


# --- log_change ---

def test_log_change_without_before_is_insert(db, make_user):
    actor = make_user("test_actor", "ADMIN")
    log_change(db, actor, "tbl_Items", "Item_ID=1", None, {"Price": 1.5})
    db.flush()
    (row,) = rows_for(db, "test_actor")
    assert (row.Action, row.Table_Name, row.Record_Key, row.User_ID) == (
        "INSERT", "tbl_Items", "Item_ID=1", actor.User_ID)


def test_log_change_without_after_is_delete(db, make_user):
    log_change(db, make_user("test_actor"), "tbl_Items", "Item_ID=1", {"Price": 1.5}, None)
    db.flush()
    assert rows_for(db, "test_actor")[0].Action == "DELETE"


def test_log_change_records_only_changed_fields(db, make_user):
    log_change(db, make_user("test_actor"), "tbl_Items", "Item_ID=1",
               {"Price": 1.45, "Name": "Καρέκλα"}, {"Price": 1.52, "Name": "Καρέκλα"})
    db.flush()
    assert rows_for(db, "test_actor")[0].Changes_JSON == '{"Price": [1.45, 1.52]}'


def test_log_change_with_no_difference_writes_nothing(db, make_user):
    log_change(db, make_user("test_actor"), "tbl_Items", "Item_ID=1", {"Price": 1.45}, {"Price": 1.45})
    db.flush()
    assert rows_for(db, "test_actor") == []


def test_log_change_never_stores_password_hash(db, make_user):
    log_change(db, make_user("test_actor"), "tbl_Users", "User_ID=1", None,
               {"Username": "x", "Password_Hash": "$argon2id$secret"})
    db.flush()
    assert "argon2" not in rows_for(db, "test_actor")[0].Changes_JSON


# --- GET /api/audit ---

@pytest.fixture
def seeded(db, make_user):
    a, b = make_user("test_a"), make_user("test_b")
    log_change(db, a, "tbl_Items", "Item_ID=1", None, {"Price": 1})
    log_change(db, a, "tbl_BOM", "BOM_ID=7", None, {"Qty": 2})
    log_change(db, b, "tbl_Items", "Item_ID=2", None, {"Price": 3})
    db.flush()


def test_audit_requires_admin(user, client):
    assert user.get("/api/audit").status_code == 403
    assert client.get("/api/audit").status_code == 401


def test_audit_filters_by_user(admin, seeded):
    body = admin.get("/api/audit", params={"user": "test_a"}).json()["data"]
    assert body["total"] == 2
    assert {r["Username"] for r in body["items"]} == {"test_a"}


def test_audit_filters_by_table_and_user(admin, seeded):
    body = admin.get("/api/audit", params={"user": "test_a", "table": "tbl_BOM"}).json()["data"]
    assert [r["Record_Key"] for r in body["items"]] == ["BOM_ID=7"]


def test_audit_is_newest_first(admin, seeded):
    items = admin.get("/api/audit", params={"user": "test_a"}).json()["data"]["items"]
    assert [r["Record_Key"] for r in items] == ["BOM_ID=7", "Item_ID=1"]


def test_audit_filters_by_date_range(admin, seeded, db):
    old = db.scalar(select(AuditLog).where(AuditLog.Record_Key == "Item_ID=1", AuditLog.Username == "test_a"))
    old.At = utcnow() - timedelta(days=10)
    db.flush()
    week_ago = (utcnow() - timedelta(days=7)).isoformat()

    recent = admin.get("/api/audit", params={"user": "test_a", "from": week_ago}).json()["data"]["items"]
    older = admin.get("/api/audit", params={"user": "test_a", "to": week_ago}).json()["data"]["items"]

    assert [r["Record_Key"] for r in recent] == ["BOM_ID=7"]
    assert [r["Record_Key"] for r in older] == ["Item_ID=1"]


def test_audit_is_paginated(admin, seeded):
    body = admin.get("/api/audit", params={"user": "test_a", "page_size": 1}).json()["data"]
    assert (len(body["items"]), body["total"]) == (1, 2)


def test_audit_log_has_no_write_endpoints(admin):
    assert admin.post("/api/audit", json={}).status_code == 405
    assert admin.delete("/api/audit").status_code == 405


# --- create-admin ---

def test_create_admin_makes_a_working_admin(db):
    create_admin(db, "test_first", "Πρώτος Admin", "first-admin-password")

    created = db.scalar(select(User).where(User.Username == "test_first"))
    assert (created.Role, created.Is_Active) == ("ADMIN", True)
    assert created.Password_Hash.startswith("$argon2id$")
    c = new_client()
    assert c.post("/api/auth/login",
                  json={"username": "test_first", "password": "first-admin-password"}).status_code == 200
    assert c.get("/api/users").status_code == 200
    assert [r.Action for r in db.scalars(select(AuditLog).where(
        AuditLog.Record_Key == f"User_ID={created.User_ID}"))] == ["INSERT"]


def test_create_admin_rejects_short_password(db):
    with pytest.raises(ValueError):
        create_admin(db, "test_first", "Πρώτος Admin", "short")


def test_create_admin_rejects_existing_username(db, make_user):
    make_user("test_first")
    with pytest.raises(ValueError):
        create_admin(db, "test_first", "Πρώτος Admin", "first-admin-password")
