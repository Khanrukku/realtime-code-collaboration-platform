from fastapi import APIRouter
from app.collab.manager import manager
from app.collab.models import RoomSnapshot

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.post("/rooms/{room_id}", response_model=RoomSnapshot)
async def create_room(room_id: str):
    return await manager.snapshot(room_id)

@router.get("/rooms/{room_id}", response_model=RoomSnapshot)
async def get_room(room_id: str):
    return await manager.snapshot(room_id)
