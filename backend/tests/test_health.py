from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "LamaplastCosting_Dev"


def test_seed_has_nine_cost_centers():
    assert client.get("/api/health").json()["cost_centers"] == 9


def test_unknown_url_is_404():
    assert client.get("/api/does-not-exist").status_code == 404