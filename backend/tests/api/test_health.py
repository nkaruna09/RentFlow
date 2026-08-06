from fastapi.testclient import TestClient

from app.main import create_app


def test_create_app_serves_health_endpoints() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    readiness = client.get("/health/ready")
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ok"


def test_docs_endpoint_is_available() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/docs")
    assert response.status_code == 200
