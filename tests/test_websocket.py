from fastapi.testclient import TestClient
from app.main import app

def test_websocket_operation_roundtrip():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/ws-room/client-a") as websocket:
            snapshot = websocket.receive_json()
            assert snapshot["type"] == "snapshot"

            websocket.send_json(
                {
                    "type": "insert",
                    "position": 0,
                    "text": "hello",
                    "base_version": 0,
                    "operation_id": "op-1",
                }
            )

            messages = [
                websocket.receive_json(),
                websocket.receive_json(),
            ]
            assert {message["type"] for message in messages} == {
                "operation",
                "ack",
            }
