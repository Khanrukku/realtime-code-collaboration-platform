from fastapi.testclient import TestClient
from app.main import app

def test_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

def test_room_snapshot():
    with TestClient(app) as client:
        response = client.post("/api/v1/rooms/test-room")
        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == "test-room"
        assert data["version"] == 0
