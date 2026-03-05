import json
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # rooms: { list_id: { user_id: websocket } }
        self._rooms: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    async def connect(self, list_id: str, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[list_id][user_id] = websocket

    def disconnect(self, list_id: str, user_id: str) -> None:
        self._rooms[list_id].pop(user_id, None)
        if not self._rooms[list_id]:
            del self._rooms[list_id]

    async def broadcast(
        self,
        list_id: str,
        event: str,
        data: dict,
        exclude_user_id: str | None = None,
    ) -> None:
        message = json.dumps({"event": event, "data": data})
        dead: list[str] = []

        for uid, ws in self._rooms.get(list_id, {}).items():
            if uid == exclude_user_id:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(uid)

        for uid in dead:
            self.disconnect(list_id, uid)

    def online_count(self, list_id: str) -> int:
        return len(self._rooms.get(list_id, {}))


# Singleton shared across the application
manager = ConnectionManager()
