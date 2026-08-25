from fastapi.testclient import TestClient

from app.main import app


def _receive_until(websocket, expected_types, max_messages=5):
    """
    Receive messages until all expected message types are seen.
    """
    received = {}

    for _ in range(max_messages):
        message = websocket.receive_json()
        received[message["type"]] = message

        if expected_types.issubset(received.keys()):
            return received

    raise AssertionError(
        f"Expected message types {expected_types}, "
        f"received {set(received.keys())}"
    )


def test_websocket_operation_roundtrip():
    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/ws-room/client-a"
        ) as websocket:

            snapshot = websocket.receive_json()

            assert snapshot["type"] == "snapshot"
            assert snapshot["data"]["version"] == 0

            websocket.send_json(
                {
                    "type": "insert",
                    "position": 0,
                    "text": "hello",
                    "base_version": 0,
                    "operation_id": "op-1",
                }
            )

            messages = _receive_until(
                websocket,
                {"operation", "ack"},
            )

            assert (
                messages["operation"]["data"]["text"]
                == "hello"
            )

            assert (
                messages["operation"]["data"]["version"]
                == 1
            )

            assert (
                messages["ack"]["operation_id"]
                == "op-1"
            )

            assert (
                messages["ack"]["version"]
                == 1
            )


def test_two_clients_receive_same_operation():
    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/multi-client-room/client-a"
        ) as client_a:

            snapshot_a = client_a.receive_json()
            assert snapshot_a["type"] == "snapshot"

            with client.websocket_connect(
                "/ws/multi-client-room/client-b"
            ) as client_b:

                snapshot_b = client_b.receive_json()
                assert snapshot_b["type"] == "snapshot"

                client_a.send_json(
                    {
                        "type": "insert",
                        "position": 0,
                        "text": "A",
                        "base_version": 0,
                        "operation_id": "op-a",
                    }
                )

                messages_a = _receive_until(
                    client_a,
                    {"operation", "ack"},
                )

                operation_b = client_b.receive_json()

                assert (
                    messages_a["operation"]["data"]["version"]
                    == 1
                )

                assert operation_b["type"] == "operation"

                assert (
                    operation_b["data"]["text"]
                    == "A"
                )

                assert (
                    operation_b["data"]["version"]
                    == 1
                )


def test_concurrent_insert_same_position_is_deterministic():
    """
    Two clients create inserts against version 0 at the same position.

    client-a sorts before client-b, so the transformation rule should
    produce deterministic text ordering.
    """
    room_id = "concurrent-insert-room"

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/ws/{room_id}/client-a"
        ) as client_a:

            client_a.receive_json()

            with client.websocket_connect(
                f"/ws/{room_id}/client-b"
            ) as client_b:

                client_b.receive_json()

                client_a.send_json(
                    {
                        "type": "insert",
                        "position": 0,
                        "text": "A",
                        "base_version": 0,
                        "operation_id": "insert-a",
                    }
                )

                _receive_until(
                    client_a,
                    {"operation", "ack"},
                )

                client_b.receive_json()

                client_b.send_json(
                    {
                        "type": "insert",
                        "position": 0,
                        "text": "B",
                        "base_version": 0,
                        "operation_id": "insert-b",
                    }
                )

                _receive_until(
                    client_b,
                    {"operation", "ack"},
                )

                broadcast_to_a = client_a.receive_json()

                assert broadcast_to_a["type"] == "operation"
                assert broadcast_to_a["data"]["version"] == 2

        snapshot = client.get(
            f"/api/v1/rooms/{room_id}"
        )

        assert snapshot.status_code == 200

        data = snapshot.json()

        assert data["version"] == 2
        assert data["text"] == "AB"


def test_stale_insert_after_delete_is_transformed():
    """
    A client submits an operation created against an older version.

    The server transforms the stale insert against the committed delete.
    """
    room_id = "insert-delete-room"

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/ws/{room_id}/client-a"
        ) as client_a:

            client_a.receive_json()

            client_a.send_json(
                {
                    "type": "insert",
                    "position": 0,
                    "text": "abcd",
                    "base_version": 0,
                    "operation_id": "seed",
                }
            )

            _receive_until(
                client_a,
                {"operation", "ack"},
            )

            with client.websocket_connect(
                f"/ws/{room_id}/client-b"
            ) as client_b:

                snapshot_b = client_b.receive_json()

                assert (
                    snapshot_b["data"]["text"]
                    == "abcd"
                )

                assert (
                    snapshot_b["data"]["version"]
                    == 1
                )

                client_a.send_json(
                    {
                        "type": "delete",
                        "position": 1,
                        "length": 2,
                        "base_version": 1,
                        "operation_id": "delete-a",
                    }
                )

                _receive_until(
                    client_a,
                    {"operation", "ack"},
                )

                client_b.receive_json()

                client_b.send_json(
                    {
                        "type": "insert",
                        "position": 4,
                        "text": "X",
                        "base_version": 1,
                        "operation_id": "insert-b",
                    }
                )

                _receive_until(
                    client_b,
                    {"operation", "ack"},
                )

                client_a.receive_json()

        snapshot = client.get(
            f"/api/v1/rooms/{room_id}"
        )

        assert snapshot.status_code == 200

        data = snapshot.json()

        assert data["version"] == 3
        assert data["text"] == "adX"


def test_future_version_operation_returns_error():
    room_id = "invalid-version-room"

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/ws/{room_id}/client-a"
        ) as websocket:

            websocket.receive_json()

            websocket.send_json(
                {
                    "type": "insert",
                    "position": 0,
                    "text": "invalid",
                    "base_version": 100,
                    "operation_id": "invalid-op",
                }
            )

            response = websocket.receive_json()

            assert response["type"] == "error"

            assert (
                "base_version cannot be ahead"
                in response["detail"]
            )


def test_reconnecting_client_receives_latest_snapshot():
    """
    A client disconnects while another client continues editing.

    When the original client reconnects, it should receive the latest
    document state and server version in the initial snapshot.
    """
    room_id = "reconnect-room"

    with TestClient(app) as client:

        # Client A joins and creates the initial document.
        with client.websocket_connect(
            f"/ws/{room_id}/client-a"
        ) as client_a:

            initial_snapshot = client_a.receive_json()

            assert initial_snapshot["type"] == "snapshot"
            assert initial_snapshot["data"]["version"] == 0

            client_a.send_json(
                {
                    "type": "insert",
                    "position": 0,
                    "text": "hello",
                    "base_version": 0,
                    "operation_id": "a-1",
                }
            )

            _receive_until(
                client_a,
                {"operation", "ack"},
            )

        # Client A is now disconnected.

        # Client B joins and continues editing.
        with client.websocket_connect(
            f"/ws/{room_id}/client-b"
        ) as client_b:

            snapshot_b = client_b.receive_json()

            assert snapshot_b["data"]["text"] == "hello"
            assert snapshot_b["data"]["version"] == 1

            client_b.send_json(
                {
                    "type": "insert",
                    "position": 5,
                    "text": " world",
                    "base_version": 1,
                    "operation_id": "b-1",
                }
            )

            _receive_until(
                client_b,
                {"operation", "ack"},
            )

        # Client A reconnects after missing B's operation.
        with client.websocket_connect(
            f"/ws/{room_id}/client-a"
        ) as reconnected_a:

            latest_snapshot = reconnected_a.receive_json()

            assert latest_snapshot["type"] == "snapshot"

            assert (
                latest_snapshot["data"]["text"]
                == "hello world"
            )

            assert (
                latest_snapshot["data"]["version"]
                == 2
            )
