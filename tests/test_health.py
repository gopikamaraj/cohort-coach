from fastapi.testclient import TestClient

from services.api.main import VERSION, app


def test_health_returns_ok_and_version() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": VERSION}
