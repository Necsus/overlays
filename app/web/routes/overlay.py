import asyncio
import json
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
from app.web.websocket import OverlayCapacityError, OverlayConnectionManager, close_overlay

OVERLAY_AUTHENTICATION_TIMEOUT_SECONDS = 5
MAX_OVERLAY_AUTHENTICATION_CHARACTERS = 512


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
        raw_message = await websocket.receive_text()
        if len(raw_message) > MAX_OVERLAY_AUTHENTICATION_CHARACTERS:
            return None
        message: object = json.loads(raw_message)
        token = parse_overlay_authentication(message)
        if token is None:
            return None

        token_hash = hash_overlay_token(token)
        database = cast(Database, websocket.app.state.database)
        async with database.access_lock:
            streamer_id = await resolve_overlay_access_key(
                database,
                plugin_slug=GIVEAWAY_PLUGIN_SLUG,
                token_hash=token_hash,
            )
            if streamer_id is None or streamer_id not in engines:
                return None
            connections.register(websocket, streamer_id=streamer_id)
        return streamer_id

    @router.websocket("/plugins/giveaway/ws")
    async def giveaway_overlay_websocket(websocket: WebSocket) -> None:
        if not connections.begin_authentication(websocket):
            await close_overlay(websocket, code=1013)
            return
        try:
            try:
                # One deadline covers acceptance, reception, lock contention and SQL.
                async with asyncio.timeout(OVERLAY_AUTHENTICATION_TIMEOUT_SECONDS):
                    await websocket.accept()
                    streamer_id = await authenticate_giveaway_overlay(websocket)
            finally:
                connections.end_authentication(websocket)

            if streamer_id is None:
                await close_overlay(websocket, code=1008)
                return
            connections.send_state(websocket, engines[streamer_id].overlay_snapshot())
            # OBS is read-only: no application messages are needed after authentication.
            message = await websocket.receive()
            if message["type"] != "websocket.disconnect":
                await close_overlay(websocket, code=1008)
        except OverlayCapacityError:
            await close_overlay(websocket, code=1013)
        except DatabaseError:
            await close_overlay(websocket, code=1011)
        except (TimeoutError, ValueError, KeyError):
            await close_overlay(websocket, code=1008)
        except (RuntimeError, WebSocketDisconnect):
            pass
        finally:
            connections.disconnect(websocket)

    return router
