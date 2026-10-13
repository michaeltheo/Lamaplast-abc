import pytest
from app.core.db import engine, get_db
from app.core.security import hash_password
from app.main import app
from app.models import User, UserPermission
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

PASSWORD = "correct-horse-battery"
_PASSWORD_HASH = hash_password(PASSWORD)  # μία φορά: το argon2 είναι επίτηδες αργό


@pytest.fixture
def db():
    """Session μέσα σε εξωτερική συναλλαγή: ακόμα και τα commit των endpoints γίνονται rollback στο τέλος."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint",
                      autoflush=False, expire_on_commit=False)
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


class ApiClient(TestClient):
    """Ελέγχει σε κάθε κλήση ότι το status_code του φακέλου είναι το πραγματικό HTTP status."""

    def request(self, method, url, **kwargs):
        response = super().request(method, url, **kwargs)
        body = response.json()
        assert set(body) == {"status_code", "success", "message", "data"}, body
        assert body["status_code"] == response.status_code
        assert body["success"] is (response.status_code < 400)
        return response


def new_client() -> ApiClient:
    # https: το session cookie είναι Secure και δεν στέλνεται πάνω από http
    return ApiClient(app, base_url="https://testserver")


@pytest.fixture
def client(db):
    return new_client()


@pytest.fixture
def make_user(db):
    def _make(username: str, role: str = "USER", *, modules: dict[str, bool] | None = None, **fields) -> User:
        fields.setdefault("Must_Change_Password", False)
        user = User(Username=username, Full_Name=username, Role=role, Password_Hash=_PASSWORD_HASH,
                    Failed_Logins=0, **fields)
        user.permissions = [UserPermission(Module=m, Can_Edit=e) for m, e in (modules or {}).items()]
        db.add(user)
        db.flush()
        return user
    return _make


@pytest.fixture
def login(db):
    def _login(username: str, password: str = PASSWORD) -> ApiClient:
        c = new_client()
        response = c.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return c
    return _login


@pytest.fixture
def admin(make_user, login):
    make_user("test_admin", "ADMIN")
    return login("test_admin")


@pytest.fixture
def user(make_user, login):
    make_user("test_user", "USER")
    return login("test_user")
