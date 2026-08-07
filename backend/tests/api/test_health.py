from fastapi.testclient import TestClient

from app.main import create_app


def test_create_app_serves_health_endpoints(monkeypatch) -> None:
    async def fake_database_is_healthy() -> bool:
        return True

    monkeypatch.setattr("app.api.v1.endpoints.health.database_is_healthy", fake_database_is_healthy)

    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    readiness = client.get("/api/v1/health/ready")
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ok"


def test_ready_endpoint_fails_when_database_is_unreachable(monkeypatch) -> None:
    async def fake_database_is_healthy() -> bool:
        raise RuntimeError("db unavailable")

    monkeypatch.setattr("app.api.v1.endpoints.health.database_is_healthy", fake_database_is_healthy)

    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert "database unavailable" in response.json()["detail"]


def test_docs_endpoint_is_available() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/docs")
    assert response.status_code == 200
