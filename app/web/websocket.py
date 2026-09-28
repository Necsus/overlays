from fastapi import WebSocket, WebSocketDisconnect


class OverlayConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, str] = {}

    def register(self, websocket: WebSocket, streamer_id: str) -> None:
        self._connections[websocket] = streamer_id

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    async def disconnect_streamer(self, streamer_id: str) -> None:
        connections = [
            websocket for websocket, owner in self._connections.items()
            if owner == streamer_id
        ]
        for websocket in connections:
            try:
                await websocket.close(code=1008)
            except (RuntimeError, WebSocketDisconnect):
                pass
            self.disconnect(websocket)

    async def send_state(
        self, websocket: WebSocket, state: dict[str, object]
    ) -> None:
        await websocket.send_json({"type": "giveaway.state", "data": state})

    async def broadcast(self, streamer_id: str, state: dict[str, object]) -> None:
        disconnected: list[WebSocket] = []
        for websocket, owner in list(self._connections.items()):
            if owner != streamer_id:
                continue
            try:
                await self.send_state(websocket, state)
            except (RuntimeError, WebSocketDisconnect):
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket)
