import json
from collections import defaultdict

from fastapi import WebSocket

# Limite defensivo: evita que um usuário sobrecarregue o servidor com conexões
# abertas simultaneamente em múltiplas abas/dispositivos.
MAX_CONNECTIONS_PER_USER = 5


class ConnectionManager:
    def __init__(self) -> None:
        # rooms: { list_id: { user_id: websocket } }
        self._rooms: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    async def connect(self, list_id: str, user_id: str, websocket: WebSocket) -> bool:
        """
        Aceita a conexão WebSocket e registra o usuário na sala da lista.

        Retorna True se a conexão foi aceita.
        Retorna False (e fecha a conexão com código 4029) se o usuário já
        atingiu o limite de conexões simultâneas em todas as listas.
        """
        # Conta conexões ativas do usuário em todas as salas
        user_connections = sum(1 for room in self._rooms.values() if user_id in room)
        if user_connections >= MAX_CONNECTIONS_PER_USER:
            await websocket.close(code=4029, reason="Too many connections")
            return False

        await websocket.accept()
        self._rooms[list_id][user_id] = websocket
        return True

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
