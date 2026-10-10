import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.application.public_limits import PublicRequestBudget

MAX_OVERLAY_HANDSHAKES = 32
MAX_OVERLAY_HANDSHAKES_PER_CLIENT = 8
MAX_OVERLAY_CONNECTIONS = 256
MAX_OVERLAY_CONNECTIONS_PER_STREAMER = 8
OVERLAY_SEND_TIMEOUT_SECONDS = 1
OVERLAY_CLOSE_TIMEOUT_SECONDS = 1
LOGGER = logging.getLogger("uvicorn.error")


async def close_overlay(websocket: WebSocket, code: int) -> None:
    try:
        async with asyncio.timeout(OVERLAY_CLOSE_TIMEOUT_SECONDS):
            await websocket.close(code=code)
    except Exception:
        # A failed transport must not retain a revoked application connection.
        pass


class OverlayCapacityError(RuntimeError):
    """A connection quota is exhausted, without evicting another owner's sockets."""


class OverlayConnectionManager:
    def __init__(
        self,
        max_handshakes: int = MAX_OVERLAY_HANDSHAKES,
        max_connections: int = MAX_OVERLAY_CONNECTIONS,
        max_per_streamer: int = MAX_OVERLAY_CONNECTIONS_PER_STREAMER,
        max_handshakes_per_client: int = MAX_OVERLAY_HANDSHAKES_PER_CLIENT,
    ) -> None:
        if min(
            max_handshakes, max_connections, max_per_streamer, max_handshakes_per_client
        ) <= 0:
            raise ValueError("Overlay connection quotas must be positive")
        self._max_handshakes = max_handshakes
        self._max_handshakes_per_client = max_handshakes_per_client
        self._max_connections = max_connections
        self._max_per_streamer = max_per_streamer
        self._handshake_budget = PublicRequestBudget(max_requests=120, max_per_client=30)
        self._pending: dict[WebSocket, str] = {}
        self._connections: dict[WebSocket, str] = {}
        self._queues: dict[WebSocket, asyncio.Queue[dict[str, object]]] = {}
        self._senders: dict[WebSocket, asyncio.Task[None]] = {}

    def begin_authentication(self, websocket: WebSocket) -> bool:
        client_id = websocket.client.host if websocket.client is not None else "unknown"
        if not self._handshake_budget.allow(client_id):
            return False
        if (
            len(self._pending) >= self._max_handshakes
            or sum(peer == client_id for peer in self._pending.values())
            >= self._max_handshakes_per_client
            or len(self._senders) >= self._max_connections
        ):
            return False
        # These operations have no awaits and run in the application's single event loop.
        self._pending[websocket] = client_id
        return True

    def end_authentication(self, websocket: WebSocket) -> None:
        self._pending.pop(websocket, None)

    def register(self, websocket: WebSocket, streamer_id: str) -> None:
        if (
            websocket in self._senders
            or len(self._senders) >= self._max_connections
            or sum(owner == streamer_id for owner in self._connections.values())
            >= self._max_per_streamer
        ):
            raise OverlayCapacityError("Overlay connection capacity exhausted")
        self._connections[websocket] = streamer_id
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=1)
        self._queues[websocket] = queue
        sender = asyncio.create_task(
            self._send_updates(websocket, queue), name="overlay-sender"
        )
        self._senders[websocket] = sender
        sender.add_done_callback(lambda finished: self._forget_sender(websocket, finished))

    def _forget_sender(self, websocket: WebSocket, sender: asyncio.Task[None]) -> None:
        if self._senders.get(websocket) is sender:
            self._senders.pop(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)
        queue = self._queues.pop(websocket, None)
        if queue is not None and not queue.empty():
            queue.get_nowait()
            queue.task_done()
        self.end_authentication(websocket)
        sender = self._senders.get(websocket)
        if sender is not None and sender is not asyncio.current_task():
            sender.cancel()

    def detach_streamer(self, streamer_id: str) -> list[WebSocket]:
        # Revocation and cancellation are synchronous: no new snapshot can be queued.
        connections = [
            websocket for websocket, owner in self._connections.items()
            if owner == streamer_id
        ]
        for websocket in connections:
            self.disconnect(websocket)
        return connections

    async def close_connections(self, connections: list[WebSocket]) -> None:
        await asyncio.gather(
            *(close_overlay(websocket, code=1008) for websocket in connections)
        )

    async def close(self) -> None:
        connections = list(self._connections)
        senders = dict(self._senders)
        for websocket in connections:
            self.disconnect(websocket)
        for sender in senders.values():
            sender.cancel()
        await asyncio.gather(*senders.values(), return_exceptions=True)
        # Done callbacks may still be queued even when gather has already returned.
        for websocket, sender in senders.items():
            self._forget_sender(websocket, sender)
        await self.close_connections(connections)

    def send_state(self, websocket: WebSocket, state: dict[str, object]) -> None:
        queue = self._queues.get(websocket)
        if queue is None:
            return
        # Intermediate snapshots may be skipped; the latest committed state wins.
        if queue.full():
            queue.get_nowait()
            queue.task_done()
        queue.put_nowait(state)

    def broadcast(self, streamer_id: str, state: dict[str, object]) -> None:
        for websocket, owner in self._connections.items():
            if owner == streamer_id:
                self.send_state(websocket, state)

    async def _send_updates(
        self, websocket: WebSocket, queue: asyncio.Queue[dict[str, object]]
    ) -> None:
        try:
            while True:
                state = await queue.get()
                try:
                    async with asyncio.timeout(OVERLAY_SEND_TIMEOUT_SECONDS):
                        await websocket.send_json({"type": "giveaway.state", "data": state})
                finally:
                    queue.task_done()
        except (RuntimeError, WebSocketDisconnect):
            self.disconnect(websocket)
            await close_overlay(websocket, code=1013)
        except Exception as error:
            LOGGER.warning("Overlay send failed: error=%s", type(error).__name__)
            self.disconnect(websocket)
            await close_overlay(websocket, code=1013)
        finally:
            self.disconnect(websocket)
