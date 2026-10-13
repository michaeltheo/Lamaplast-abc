import json

import pytest
from app.core.db import get_db
from app.core.deps import require_module, require_role
from app.models import AuditLog, User
from conftest import PASSWORD, new_client
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

NEW_USER = {"Username": "test_new", "Full_Name": "Νέος Χρήστης", "Email": "new@example.com",
            "Role": "EXPERT", "password": "temporary-pass-1"}


def audit_rows(db, table: str, key: str) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).where(AuditLog.Table_Name == table, AuditLog.Record_Key == key)
                           .order_by(AuditLog.Audit_ID)))



def test_user_role_gets_403_on_create_user(user):
    assert user.post("/api/users", json=NEW_USER).status_code == 403


def test_expert_gets_403_on_users(make_user, login):
    make_user("test_expert", "EXPERT")
    c = login("test_expert")
    assert c.get("/api/users").status_code == 403
    assert c.post("/api/users", json=NEW_USER).status_code == 403


def test_anonymous_gets_401_on_users(client):
    assert client.get("/api/users").status_code == 401
    assert client.post("/api/users", json=NEW_USER).status_code == 401


def test_demoted_admin_loses_access_on_next_request(admin, db):
    db.scalar(select(User).where(User.Username == "test_admin")).Role = "USER"
    db.flush()
    assert admin.get("/api/users").status_code == 403


# --- δημιουργία ---

def test_admin_creates_user_who_must_change_password(admin, db):
    response = admin.post("/api/users", json=NEW_USER)

    assert response.status_code == 201
    body = response.json()["data"]
    assert (body["Username"], body["Role"], body["Must_Change_Password"]) == ("test_new", "EXPERT", True)
    assert "password" not in body and "Password_Hash" not in body

    created = db.get(User, body["User_ID"])
    assert created.Password_Hash.startswith("$argon2id$")
    assert created.Created_By == "test_admin"
    c = new_client()
    assert c.post("/api/auth/login", json={"username": "test_new", "password": "temporary-pass-1"}).status_code == 200


def test_create_user_is_audited_without_the_password(admin, db):
    user_id = admin.post("/api/users", json=NEW_USER).json()["data"]["User_ID"]

    (row,) = audit_rows(db, "tbl_Users", f"User_ID={user_id}")
    assert (row.Action, row.Username) == ("INSERT", "test_admin")
    assert "Password_Hash" not in row.Changes_JSON
    assert "temporary-pass-1" not in row.Changes_JSON
    assert json.loads(row.Changes_JSON)["Role"] == [None, "EXPERT"]


def test_duplicate_username_is_409(admin):
    assert admin.post("/api/users", json=NEW_USER).status_code == 201
    assert admin.post("/api/users", json=NEW_USER).status_code == 409


@pytest.mark.parametrize("patch", [{"Role": "SUPERUSER"}, {"password": "short"}, {"Username": ""}])
def test_invalid_new_user_is_422(admin, patch):
    assert admin.post("/api/users", json={**NEW_USER, **patch}).status_code == 422


def test_list_users_is_paginated(admin, make_user):
    make_user("test_other")
    body = admin.get("/api/users", params={"page_size": 200}).json()["data"]
    assert {"test_admin", "test_other"} <= {u["Username"] for u in body["items"]}
    assert body["total"] >= 2


# --- αλλαγή ---

def test_admin_updates_user_and_audit_has_before_and_after(admin, make_user, db):
    target = make_user("test_target", "USER")

    response = admin.put(f"/api/users/{target.User_ID}", json={"Role": "EXPERT", "Full_Name": "Άλλο Όνομα"})

    assert response.status_code == 200
    assert response.json()["data"]["Role"] == "EXPERT"
    (row,) = audit_rows(db, "tbl_Users", f"User_ID={target.User_ID}")
    assert row.Action == "UPDATE"
    assert json.loads(row.Changes_JSON) == {"Role": ["USER", "EXPERT"], "Full_Name": ["test_target", "Άλλο Όνομα"]}


def test_update_unknown_user_is_404(admin):
    assert admin.put("/api/users/999999999", json={"Role": "USER"}).status_code == 404


def test_admin_password_reset_forces_change_and_kills_old_sessions(admin, make_user, login):
    target = make_user("test_target")
    old_session = login("test_target")

    admin.put(f"/api/users/{target.User_ID}", json={"password": "reset-by-admin-01"})

    assert old_session.get("/api/auth/me").status_code == 401
    fresh = login("test_target", "reset-by-admin-01")
    assert fresh.get("/api/auth/me").json()["data"]["Must_Change_Password"] is True


def test_deactivated_user_cannot_login(admin, make_user):
    target = make_user("test_target")
    admin.put(f"/api/users/{target.User_ID}", json={"Is_Active": False})
    response = new_client().post("/api/auth/login", json={"username": "test_target", "password": PASSWORD})
    assert response.status_code == 401


def test_admin_unlocks_a_locked_account(admin, make_user, db):
    target = make_user("test_target")
    c = new_client()
    for _ in range(5):
        c.post("/api/auth/login", json={"username": "test_target", "password": "wrong-password-123"})

    admin.put(f"/api/users/{target.User_ID}", json={"unlock": True})

    assert c.post("/api/auth/login", json={"username": "test_target", "password": PASSWORD}).status_code == 200
    assert "UNLOCK" in [r.Action for r in audit_rows(db, "tbl_Users", f"User_ID={target.User_ID}")]


def test_admin_cannot_demote_or_deactivate_themselves(admin):
    me = admin.get("/api/auth/me").json()["data"]["User_ID"]
    assert admin.put(f"/api/users/{me}", json={"Role": "USER"}).status_code == 409
    assert admin.put(f"/api/users/{me}", json={"Is_Active": False}).status_code == 409


# --- δικαιώματα ενοτήτων ---

def test_admin_sets_permissions_replacing_the_old_ones(admin, make_user, db):
    target = make_user("test_target", "EXPERT", modules={"ITEMS": True})

    response = admin.put(f"/api/users/{target.User_ID}/permissions",
                         json=[{"Module": "BOM", "Can_Edit": True}, {"Module": "PRICES", "Can_Edit": False}])

    assert response.status_code == 200
    assert response.json()["data"]["permissions"] == [{"Module": "BOM", "Can_Edit": True},
                                              {"Module": "PRICES", "Can_Edit": False}]
    (row,) = audit_rows(db, "tbl_UserPermissions", f"User_ID={target.User_ID}")
    assert json.loads(row.Changes_JSON) == {"BOM": [None, True], "ITEMS": [True, None], "PRICES": [None, False]}


def test_unknown_module_is_422(admin, make_user):
    target = make_user("test_target", "EXPERT")
    response = admin.put(f"/api/users/{target.User_ID}/permissions", json=[{"Module": "NOPE", "Can_Edit": True}])
    assert response.status_code == 422


def test_duplicate_module_is_422(admin, make_user):
    target = make_user("test_target", "EXPERT")
    response = admin.put(f"/api/users/{target.User_ID}/permissions",
                         json=[{"Module": "BOM", "Can_Edit": True}, {"Module": "BOM", "Can_Edit": False}])
    assert response.status_code == 422


def test_user_gets_403_on_permissions(user, make_user):
    target = make_user("test_target", "EXPERT")
    assert user.put(f"/api/users/{target.User_ID}/permissions", json=[]).status_code == 403


# --- require_role / require_module πάνω σε δοκιμαστικά endpoints ---

@pytest.fixture
def guarded(db):
    """Μικρό app: τα πραγματικά endpoints με require_module έρχονται σε επόμενες φάσεις."""
    app = FastAPI()
    app.dependency_overrides[get_db] = lambda: db

    @app.get("/bom", dependencies=[Depends(require_module("BOM"))])
    def read_bom():
        return "ok"

    @app.post("/bom", dependencies=[Depends(require_module("BOM", edit=True))])
    def write_bom():
        return "ok"

    @app.get("/staff", dependencies=[Depends(require_role("ADMIN", "EXPERT"))])
    def staff():
        return "ok"

    def as_user(logged_in: TestClient) -> TestClient:
        c = TestClient(app, base_url="https://testserver")
        c.cookies = logged_in.cookies
        return c
    return as_user


def codes(c: TestClient) -> tuple[int, int]:
    return c.get("/bom").status_code, c.post("/bom").status_code


def test_admin_passes_every_module_check(guarded, admin):
    assert codes(guarded(admin)) == (200, 200)


def test_expert_with_edit_permission_reads_and_writes(guarded, make_user, login):
    make_user("test_e", "EXPERT", modules={"BOM": True})
    assert codes(guarded(login("test_e"))) == (200, 200)


def test_expert_with_read_only_permission_cannot_write(guarded, make_user, login):
    make_user("test_e", "EXPERT", modules={"BOM": False})
    assert codes(guarded(login("test_e"))) == (200, 403)


def test_expert_without_the_module_is_blocked(guarded, make_user, login):
    make_user("test_e", "EXPERT", modules={"ITEMS": True})
    assert codes(guarded(login("test_e"))) == (403, 403)


def test_user_role_never_writes_even_with_can_edit(guarded, make_user, login):
    make_user("test_u", "USER", modules={"BOM": True})
    assert codes(guarded(login("test_u"))) == (200, 403)


def test_require_role_accepts_listed_roles_only(guarded, admin, user):
    assert guarded(admin).get("/staff").status_code == 200
    assert guarded(user).get("/staff").status_code == 403


def test_guarded_endpoint_without_login_is_401(guarded, db):
    assert guarded(new_client()).get("/bom").status_code == 401
