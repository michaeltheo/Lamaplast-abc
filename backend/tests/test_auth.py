from datetime import timedelta

from conftest import PASSWORD, new_client
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    SESSION_COOKIE,
    create_session_token,
    hash_password,
    read_session_token,
    utcnow,
    verify_password,
)
from app.models import AuditLog


def audit_actions(db, username: str) -> list[str]:
    return list(db.scalars(select(AuditLog.Action).where(AuditLog.Username == username).order_by(AuditLog.Audit_ID)))


def bad_login(client, username: str, password: str = "wrong-password-123"):
    return client.post("/api/auth/login", json={"username": username, "password": password})



def test_password_is_hashed_with_argon2id_not_stored_in_clear():
    hashed = hash_password(PASSWORD)
    assert hashed.startswith("$argon2id$")
    assert PASSWORD not in hashed


def test_verify_password_accepts_right_and_rejects_wrong():
    hashed = hash_password(PASSWORD)
    assert verify_password(hashed, PASSWORD) is True
    assert verify_password(hashed, "something-else") is False


def test_tampered_session_token_is_rejected(make_user):
    token = create_session_token(make_user("test_u"))
    assert read_session_token(token) is not None
    assert read_session_token(("X" if token[0] != "X" else "Y") + token[1:]) is None
    assert read_session_token("garbage") is None


# --- login ---

def test_login_sets_cookie_and_me_returns_the_user(make_user, client):
    make_user("test_u", "EXPERT", modules={"BOM": True})

    response = client.post("/api/auth/login", json={"username": "test_u", "password": PASSWORD})

    assert response.status_code == 200
    me = client.get("/api/auth/me").json()["data"]
    assert (me["Username"], me["Role"]) == ("test_u", "EXPERT")
    assert me["permissions"] == [{"Module": "BOM", "Can_Edit": True}]
    assert "Password_Hash" not in me


def test_session_cookie_is_httponly_secure_and_samesite(make_user, client):
    make_user("test_u")
    header = client.post("/api/auth/login", json={"username": "test_u", "password": PASSWORD}).headers["set-cookie"]
    lowered = header.lower()
    assert header.startswith(f"{SESSION_COOKIE}=")
    assert "httponly" in lowered and "secure" in lowered and "samesite=lax" in lowered


def test_wrong_password_is_401(make_user, client):
    make_user("test_u")
    assert bad_login(client, "test_u").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_unknown_user_gets_same_response_as_wrong_password(make_user, client):
    make_user("test_u")
    wrong = bad_login(client, "test_u")
    unknown = bad_login(client, "test_nobody")
    assert (unknown.status_code, unknown.json()) == (wrong.status_code, wrong.json())


def test_inactive_user_cannot_login(make_user, client):
    make_user("test_u", Is_Active=False)
    assert client.post("/api/auth/login", json={"username": "test_u", "password": PASSWORD}).status_code == 401


def test_me_without_cookie_is_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_the_session(make_user, login):
    make_user("test_u")
    c = login("test_u")
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401


# --- κλείδωμα ---

def test_account_locks_after_five_wrong_passwords(make_user, client, db):
    user = make_user("test_u")
    for _ in range(settings.max_failed_logins):
        assert bad_login(client, "test_u").status_code == 401

    # ακόμα και ο σωστός κωδικός απορρίπτεται όσο είναι κλειδωμένος
    assert client.post("/api/auth/login", json={"username": "test_u", "password": PASSWORD}).status_code == 401
    db.refresh(user)
    assert user.Locked_Until > utcnow()
    assert "LOCK" in audit_actions(db, "test_u")


def test_four_wrong_passwords_do_not_lock(make_user, client):
    make_user("test_u")
    for _ in range(settings.max_failed_logins - 1):
        bad_login(client, "test_u")
    assert client.post("/api/auth/login", json={"username": "test_u", "password": PASSWORD}).status_code == 200


def test_successful_login_resets_the_failure_counter(make_user, client, db):
    user = make_user("test_u")
    bad_login(client, "test_u")
    client.post("/api/auth/login", json={"username": "test_u", "password": PASSWORD})
    db.refresh(user)
    assert user.Failed_Logins == 0


def test_lock_expires(make_user, client, db):
    make_user("test_u", Locked_Until=utcnow() - timedelta(minutes=1))
    assert client.post("/api/auth/login", json={"username": "test_u", "password": PASSWORD}).status_code == 200


# --- audit ---

def test_every_login_attempt_is_written_to_audit_log(make_user, client, db):
    make_user("test_u")
    bad_login(client, "test_u")
    client.post("/api/auth/login", json={"username": "test_u", "password": PASSWORD})
    bad_login(client, "test_nobody")

    assert audit_actions(db, "test_u") == ["LOGIN_FAILED", "LOGIN"]
    assert audit_actions(db, "test_nobody") == ["LOGIN_FAILED"]


def test_password_never_appears_in_audit_log(make_user, client, db):
    make_user("test_u")
    bad_login(client, "test_u", "my-secret-typo-999")
    rows = db.scalars(select(AuditLog).where(AuditLog.Username == "test_u")).all()
    assert all("my-secret-typo-999" not in f"{r.Changes_JSON}{r.Notes}" for r in rows)


# --- αλλαγή κωδικού ---

def test_must_change_password_blocks_everything_except_auth(make_user, login):
    make_user("test_u", Must_Change_Password=True)
    c = login("test_u")
    assert c.get("/api/auth/me").json()["data"]["Must_Change_Password"] is True
    assert c.get("/api/lookups/bssg").status_code == 403


def test_change_password_unblocks_and_new_password_works(make_user, login, client):
    make_user("test_u", Must_Change_Password=True)
    c = login("test_u")

    response = c.post("/api/auth/change-password",
                      json={"current_password": PASSWORD, "new_password": "brand-new-password-1"})

    assert response.status_code == 200
    assert c.get("/api/lookups/bssg").status_code == 200
    assert bad_login(client, "test_u", PASSWORD).status_code == 401
    assert client.post("/api/auth/login",
                       json={"username": "test_u", "password": "brand-new-password-1"}).status_code == 200


def test_change_password_requires_the_current_one(make_user, login):
    make_user("test_u")
    c = login("test_u")
    response = c.post("/api/auth/change-password",
                      json={"current_password": "not-my-password", "new_password": "brand-new-password-1"})
    assert response.status_code == 400


def test_short_new_password_is_rejected(make_user, login):
    make_user("test_u")
    c = login("test_u")
    response = c.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "short"})
    assert response.status_code == 422


def test_changing_password_invalidates_older_sessions(make_user, login):
    make_user("test_u")
    old, current = login("test_u"), login("test_u")
    current.post("/api/auth/change-password",
                 json={"current_password": PASSWORD, "new_password": "brand-new-password-1"})
    assert old.get("/api/auth/me").status_code == 401
    assert current.get("/api/auth/me").status_code == 200


def test_deactivated_user_loses_the_session_immediately(make_user, login, db):
    user = make_user("test_u")
    c = login("test_u")
    user.Is_Active = False
    db.flush()
    assert c.get("/api/auth/me").status_code == 401


# --- CSRF ---

def test_post_from_foreign_origin_is_rejected(make_user, login):
    make_user("test_u")
    c = login("test_u")
    assert c.post("/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403


def test_post_from_allowed_origin_passes(make_user):
    make_user("test_u")
    response = new_client().post("/api/auth/login", json={"username": "test_u", "password": PASSWORD},
                                 headers={"Origin": settings.cors_origins[0]})
    assert response.status_code == 200
