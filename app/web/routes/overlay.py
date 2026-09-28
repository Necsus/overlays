import asyncio
from pathlib import Path
from typing import cast

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.application.overlay_access import (
    GIVEAWAY_PLUGIN_SLUG,
    hash_overlay_token,
    parse_overlay_authentication,
)
from app.domain.giveaway import GiveawayEngine
from app.infrastructure.database import Database, DatabaseError
from app.infrastructure.overlay_access import resolve_overlay_access_key
from app.web.websocket import OverlayConnectionManager


def create_overlay_router(
    engines: dict[str, GiveawayEngine],
    connections: OverlayConnectionManager,
    static_directory: Path,
) -> APIRouter:
    router = APIRouter()

    @router.get("/plugins/giveaway/overlay", response_class=FileResponse)
    def overlay() -> FileResponse:
        return FileResponse(static_directory / "overlay.html")

    async def authenticate_giveaway_overlay(
        websocket: WebSocket,
    ) -> str | None:
        await websocket.accept()

        try:
            async with asyncio.timeout(5):
                message: object = await websocket.receive_json()
        except WebSocketDisconnect:
            return None
        except (TimeoutError, ValueError):
            await websocket.close(code=1008)
            return None

        token = parse_overlay_authentication(message)
        if token is None:
            await websocket.close(code=1008)
            return None

        token_hash = hash_overlay_token(token)
        database = cast(Database, websocket.app.state.database)
        async with database.access_lock:
            try:
                streamer_id = await resolve_overlay_access_key(
                    database,
                    plugin_slug=GIVEAWAY_PLUGIN_SLUG,
                    token_hash=token_hash,
                )
            except DatabaseError:
                await websocket.close(code=1011)
                return None

            if streamer_id is None or streamer_id not in engines:
                await websocket.close(code=1008)
                return None

            connections.register(websocket, streamer_id=streamer_id)
        return streamer_id

    @router.websocket("/plugins/giveaway/ws")
    async def giveaway_overlay_websocket(websocket: WebSocket) -> None:
        streamer_id = await authenticate_giveaway_overlay(websocket)
        if streamer_id is None:
            return
        try:
            await connections.send_state(websocket, engines[streamer_id].overlay_snapshot())
            while True:
                _ = await websocket.receive_text()
        except (RuntimeError, WebSocketDisconnect):
            connections.disconnect(websocket)

    return router
