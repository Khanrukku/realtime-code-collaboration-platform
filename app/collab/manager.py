import asyncio

from fastapi import WebSocket

from app.collab.document import Room
from app.collab.models import Operation, RoomSnapshot
from app.core.config import settings


class CollaborationManager:
    """
    Manages collaborative editing rooms and connected WebSocket clients.

    Responsibilities:
      - create and retrieve collaboration rooms
      - maintain room membership
      - provide current document snapshots
      - apply versioned operations
      - broadcast committed operations to connected clients
      - clean up disconnected clients
    """

    def __init__(self):
        self._rooms: dict[str, Room] = {}
        self._rooms_lock = asyncio.Lock()

    async def get_or_create(
        self,
        room_id: str,
    ) -> Room:
        """
        Return an existing room or create it atomically.
        """
        async with self._rooms_lock:
            room = self._rooms.get(room_id)

            if room is None:
                room = Room(
                    room_id,
                    max_history=settings.max_history,
                )

                self._rooms[room_id] = room

            return room

    async def snapshot(
        self,
        room_id: str,
    ) -> RoomSnapshot:
        """
        Return the latest document snapshot for a room.
        """
        room = await self.get_or_create(
            room_id
        )

        async with room.lock:
            return RoomSnapshot(
                room_id=room_id,
                text=room.document.text,
                version=room.document.version,
                clients=len(room.clients),
            )

    async def connect(
        self,
        room_id: str,
        websocket: WebSocket,
    ) -> Room:
        """
        Accept a WebSocket connection and synchronize the client
        with the latest server-side document state.

        This snapshot also allows reconnecting clients to recover
        changes that happened while they were disconnected.
        """
        room = await self.get_or_create(
            room_id
        )

        await websocket.accept()

        async with room.lock:
            room.clients.add(websocket)

            snapshot = RoomSnapshot(
                room_id=room_id,
                text=room.document.text,
                version=room.document.version,
                clients=len(room.clients),
            )

        await websocket.send_json(
            {
                "type": "snapshot",
                "data": snapshot.model_dump(),
            }
        )

        return room

    async def disconnect(
        self,
        room: Room,
        websocket: WebSocket,
    ):
        """
        Remove a disconnected WebSocket client from the room.
        """
        async with room.lock:
            room.clients.discard(
                websocket
            )

    async def apply_and_broadcast(
        self,
        room: Room,
        operation: Operation,
    ):
        """
        Apply a client operation to the shared document and broadcast
        the committed operation to all currently connected clients.

        Document mutation is protected by the room-level asyncio lock
        so concurrent operations are serialized deterministically.
        """
        async with room.lock:
            committed = room.document.apply(
                operation
            )

            clients = list(
                room.clients
            )

        payload = {
            "type": "operation",
            "data": committed.model_dump(),
        }

        dead_clients = []

        for client in clients:
            try:
                await client.send_json(
                    payload
                )

            except Exception:
                dead_clients.append(
                    client
                )

        # Remove clients whose connection failed during broadcast.
        if dead_clients:
            async with room.lock:
                for client in dead_clients:
                    room.clients.discard(
                        client
                    )

        return committed


manager = CollaborationManager()
