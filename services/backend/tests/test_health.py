from fastapi.testclient import TestClient
from backend.main import create_app


def test_health_endpoint(tmp_path):
    client = TestClient(create_app(data_root=tmp_path))
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "AI Lacrosse Coach API"
