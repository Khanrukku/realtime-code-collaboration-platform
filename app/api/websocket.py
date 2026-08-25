from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.collab.manager import manager
from app.collab.models import Operation

router = APIRouter()

@router.websocket("/ws/{room_id}/{client_id}")
async def collaboration_socket(
    websocket: WebSocket,
    room_id: str,
    client_id: str,
):
    room = await manager.connect(room_id, websocket)

    try:
        while True:
            payload = await websocket.receive_json()

            try:
                operation = Operation(**payload, client_id=client_id)
                committed = await manager.apply_and_broadcast(room, operation)

                await websocket.send_json(
                    {
                        "type": "ack",
                        "operation_id": committed.operation_id,
                        "version": committed.version,
                    }
                )

            except (ValidationError, ValueError) as exc:
                await websocket.send_json(
                    {"type": "error", "detail": str(exc)}
                )

    except WebSocketDisconnect:
        await manager.disconnect(room, websocket)
