from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.adapters.repositories.mongo_member_repo import MongoMemberRepository
from app.adapters.services.jwt_token_service import JWTTokenService
from app.infra.db.mongodb import get_database
from app.infra.websocket.connection_manager import manager

router = APIRouter(tags=["websocket"])
_token_service = JWTTokenService()


@router.websocket("/ws/lists/{list_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    list_id: str,
    token: str = Query(...),
) -> None:
    # 1. Validate JWT before accepting connection
    try:
        user_id = _token_service.decode_token(token)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # 2. Verify list membership
    db = get_database()
    member_repo = MongoMemberRepository(db)
    membership = await member_repo.find(list_id, user_id)
    if not membership:
        await websocket.close(code=4003, reason="Not a member of this list")
        return

    # 3. Accept and register in room (retorna False se limite de conexões atingido)
    connected = await manager.connect(list_id, user_id, websocket)
    if not connected:
        return

    try:
        while True:
            # Keep connection alive; client sends pings if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(list_id, user_id)
