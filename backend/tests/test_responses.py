import pytest
from conftest import PASSWORD
from fastapi.testclient import TestClient

from app.main import app

OPERATIONS = [(method.upper(), path, operation)
              for path, methods in app.openapi()["paths"].items() for method, operation in methods.items()]


def test_endpoint_list_is_not_empty():
    assert OPERATIONS  # αλλιώς ο παρακάτω έλεγχος δεν θα έτρεχε για κανένα endpoint


@pytest.mark.parametrize(("method", "path", "operation"), OPERATIONS, ids=[f"{m} {p}" for m, p, _ in OPERATIONS])
def test_every_endpoint_declares_the_envelope_as_its_response_schema(method, path, operation):
    for code, response in operation["responses"].items():
        ref = response["content"]["application/json"]["schema"]["$ref"]
        assert ref.startswith("#/components/schemas/ApiResponse_"), f"{method} {path} {code}: {ref}"


def test_success_carries_the_data_and_the_http_status(client):
    response = client.get("/api/health")
    body = response.json()
    assert (body["status_code"], body["success"], body["message"]) == (200, True, None)
    assert body["data"]["status"] == "ok"


def test_created_reports_201_in_the_body(admin):
    response = admin.post("/api/users", json={"Username": "test_new", "Full_Name": "Νέος",
                                              "password": "temporary-pass-1"})
    assert (response.status_code, response.json()["status_code"]) == (201, 201)


def test_endpoints_without_data_return_a_message(user):
    body = user.post("/api/auth/logout").json()
    assert (body["status_code"], body["data"]) == (200, None)
    assert body["message"]


def test_error_has_message_and_no_data(client):
    response = client.get("/api/auth/me")
    assert response.json() == {"status_code": 401, "success": False, "message": "Απαιτείται σύνδεση", "data": None}


def test_forbidden_is_enveloped(user):
    body = user.get("/api/users").json()
    assert (body["status_code"], body["success"], body["data"]) == (403, False, None)


def test_unknown_url_is_enveloped(client):
    body = client.get("/api/does-not-exist").json()
    assert (body["status_code"], body["success"]) == (404, False)


def test_wrong_method_is_enveloped(client):
    assert client.delete("/api/health").json()["status_code"] == 405


def test_validation_error_lists_the_fields(client):
    response = client.post("/api/auth/login", json={"username": "test_u"})
    body = response.json()
    assert (response.status_code, body["status_code"], body["success"]) == (422, 422, False)
    assert body["data"] == [{"field": "body.password", "message": body["data"][0]["message"]}]


def test_validation_error_does_not_echo_the_submitted_password(client):
    secret = "leaked-secret-" + "x" * 200
    response = client.post("/api/auth/login", json={"username": "test_u", "password": secret})
    assert response.status_code == 422
    assert "leaked-secret" not in response.text


def test_csrf_rejection_is_enveloped(make_user, login):
    make_user("test_u")
    response = login("test_u").post("/api/auth/logout", headers={"Origin": "https://evil.example"})
    assert response.json()["status_code"] == 403


def test_unexpected_error_is_a_500_envelope_without_internals(db):
    @app.get("/api/_boom", include_in_schema=False)
    def boom():
        raise RuntimeError("database password is hunter2")

    try:
        response = TestClient(app, base_url="https://testserver", raise_server_exceptions=False).get("/api/_boom")
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", None) != "/api/_boom"]

    assert response.status_code == 500
    assert response.json() == {"status_code": 500, "success": False, "message": "Εσωτερικό σφάλμα", "data": None}


def test_login_envelope_still_sets_the_cookie(make_user, client):
    make_user("test_u")
    response = client.post("/api/auth/login", json={"username": "test_u", "password": PASSWORD})
    assert response.json()["data"]["Username"] == "test_u"
    assert "set-cookie" in response.headers
