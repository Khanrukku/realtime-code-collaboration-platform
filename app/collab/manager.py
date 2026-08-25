import asyncio
from fastapi import WebSocket

from app.collab.document import Room
from app.collab.models import Operation, RoomSnapshot
from app.core.config import settings

class CollaborationManager:
    def __init__(self):
        self._rooms: dict[str, Room] = {}
        self._rooms_lock = asyncio.Lock()

    async def get_or_create(self, room_id: str) -> Room:
        async with self._rooms_lock:
            room = self._rooms.get(room_id)
            if room is None:
                room = Room(room_id, max_history=settings.max_history)
                self._rooms[room_id] = room
            return room

    async def snapshot(self, room_id: str) -> RoomSnapshot:
        room = await self.get_or_create(room_id)
        async with room.lock:
            return RoomSnapshot(
                room_id=room_id,
                text=room.document.text,
                version=room.document.version,
                clients=len(room.clients),
            )

    async def connect(self, room_id: str, websocket: WebSocket):
        room = await self.get_or_create(room_id)
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
            {"type": "snapshot", "data": snapshot.model_dump()}
        )
        return room

    async def disconnect(self, room: Room, websocket: WebSocket):
        async with room.lock:
            room.clients.discard(websocket)

    async def apply_and_broadcast(self, room: Room, operation: Operation):
        async with room.lock:
            committed = room.document.apply(operation)
            clients = list(room.clients)

        payload = {"type": "operation", "data": committed.model_dump()}
        dead_clients = []

        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                dead_clients.append(client)

        if dead_clients:
            async with room.lock:
                for client in dead_clients:
                    room.clients.discard(client)

        return committed

manager = CollaborationManager()
