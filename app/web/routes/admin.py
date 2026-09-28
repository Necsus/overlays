from pathlib import Path
from typing import Annotated, cast
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse

from app.application.commands import GiveawayCommandHandler
from app.application.overlay_access import (
    GIVEAWAY_PLUGIN_SLUG,
    generate_overlay_token,
    hash_overlay_token,
)
from app.application.session import SessionIdentity
from app.core.configuration import ApplicationConfiguration
from app.infrastructure.database import Database, DatabaseError
from app.infrastructure.history import (
    list_giveaways,
    load_command_prefix,
    load_giveaway_detail,
    save_command_prefix,
)
from app.infrastructure.overlay_access import (
    load_overlay_access_key_rotated_at,
    rotate_overlay_access_key,
)
from app.infrastructure.streamers import load_streamer
from app.infrastructure.twitch import GiveawayTwitchBot
from app.web.dependencies import require_session_identity
from app.web.websocket import OverlayConnectionManager

ADMIN_PAGE = Path(__file__).resolve().parents[1] / "static" / "admin" / "admin.html"
router = APIRouter()
SessionDependency = Annotated[SessionIdentity, Depends(require_session_identity)]


@router.get("/admin", response_class=FileResponse)
def admin_page() -> FileResponse:
    return FileResponse(ADMIN_PAGE)


@router.get("/api/admin/session")
async def admin_session(request: Request, identity: SessionDependency) -> dict[str, object]:
    database = cast(Database, request.app.state.database)
    try:
        streamer = await load_streamer(database, identity.twitch_user_id)
    except DatabaseError:
        raise HTTPException(status_code=503, detail="Unable to load the Twitch identity") from None
    if streamer is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    configuration = cast(ApplicationConfiguration, request.app.state.configuration)
    twitch_bot = cast(GiveawayTwitchBot | None, request.app.state.twitch_bot)
    if twitch_bot is None:
        chat_status = "disabled"
    elif twitch_bot.chat_subscription_ready_for(identity.twitch_user_id):
        chat_status = "ready"
    else:
        chat_status = "degraded"
    identity_data = {
        "twitch_user_id": streamer.twitch_user_id,
        "login": streamer.login,
        "display_name": streamer.display_name,
    }
    return {
        "session": {**identity_data, "profile_image_url": streamer.profile_image_url},
        "active_streamer": identity_data,
        "bot": {"twitch_user_id": configuration.twitch.bot_id,
                "login": configuration.twitch.bot_login},
        "chat": {"status": chat_status},
    }


@router.post("/api/admin/plugins/giveaway/overlay-access/rotate")
async def rotate_giveaway_overlay_access(
    request: Request, response: Response, identity: SessionDependency
) -> dict[str, str]:
    token = generate_overlay_token()
    database = cast(Database, request.app.state.database)
    overlay_connections = cast(OverlayConnectionManager, request.app.state.overlay_connections)
    async with database.access_lock:
        try:
            rotated_at = await rotate_overlay_access_key(
                database, streamer_id=identity.twitch_user_id,
                plugin_slug=GIVEAWAY_PLUGIN_SLUG, token_hash=hash_overlay_token(token),
            )
        except DatabaseError:
            await overlay_connections.disconnect_streamer(identity.twitch_user_id)
            raise HTTPException(status_code=500, detail="Unable to rotate the overlay access key") from None
        await overlay_connections.disconnect_streamer(identity.twitch_user_id)
    response.headers["Cache-Control"] = "no-store"
    return {"overlay_url": f"{str(request.base_url).rstrip('/')}/plugins/giveaway/overlay#{token}",
            "rotated_at": rotated_at}


@router.get("/api/admin/plugins/giveaway/overlay-access")
async def giveaway_overlay_access_status(
    request: Request, response: Response, identity: SessionDependency
) -> dict[str, object]:
    database = cast(Database, request.app.state.database)
    try:
        rotated_at = await load_overlay_access_key_rotated_at(
            database, streamer_id=identity.twitch_user_id, plugin_slug=GIVEAWAY_PLUGIN_SLUG
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Unable to load the overlay access status") from None
    response.headers["Cache-Control"] = "no-store"
    return {"configured": rotated_at is not None, "rotated_at": rotated_at}


@router.get("/api/admin/plugins/giveaway/history")
async def giveaway_history(
    request: Request,
    identity: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    before: datetime | None = None,
    before_id: str | None = None,
) -> dict[str, object]:
    if (before is None) != (before_id is None):
        raise HTTPException(status_code=400, detail="Both cursor fields are required")
    database = cast(Database, request.app.state.database)
    try:
        rows = await list_giveaways(
            database, identity.twitch_user_id, limit + 1, before, before_id
        )
    except DatabaseError:
        raise HTTPException(status_code=503, detail="Unable to load giveaway history") from None
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = None
    if has_more and rows:
        next_cursor = {"before": rows[-1]["created_at"], "before_id": rows[-1]["id"]}
    return {"items": rows, "next_cursor": next_cursor}


@router.get("/api/admin/plugins/giveaway/history/{giveaway_id}")
async def giveaway_history_detail(
    request: Request, giveaway_id: str, identity: SessionDependency
) -> dict[str, object]:
    database = cast(Database, request.app.state.database)
    try:
        detail = await load_giveaway_detail(database, identity.twitch_user_id, giveaway_id)
    except DatabaseError:
        raise HTTPException(status_code=503, detail="Unable to load giveaway history") from None
    if detail is None:
        raise HTTPException(status_code=404, detail="Giveaway not found")
    return detail


@router.get("/api/admin/plugins/giveaway/preferences")
async def giveaway_preferences(
    request: Request, identity: SessionDependency
) -> dict[str, str]:
    database = cast(Database, request.app.state.database)
    if await load_streamer(database, identity.twitch_user_id) is None:
        raise HTTPException(status_code=404, detail="Streamer not found")
    try:
        prefix = await load_command_prefix(database, identity.twitch_user_id)
    except DatabaseError:
        raise HTTPException(status_code=503, detail="Unable to load preferences") from None
    return {"command_prefix": prefix}


@router.patch("/api/admin/plugins/giveaway/preferences")
async def update_giveaway_preferences(
    request: Request, identity: SessionDependency
) -> dict[str, str]:
    database = cast(Database, request.app.state.database)
    if await load_streamer(database, identity.twitch_user_id) is None:
        raise HTTPException(status_code=404, detail="Streamer not found")
    try:
        payload = await request.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("command_prefix"), str):
            raise ValueError
        prefix = payload["command_prefix"].strip()
        if not 1 <= len(prefix) <= 5:
            raise ValueError
    except (ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(status_code=422, detail="Invalid command prefix") from None
    try:
        await save_command_prefix(database, identity.twitch_user_id, prefix)
    except DatabaseError:
        raise HTTPException(status_code=503, detail="Unable to save preferences") from None
    handlers = cast(dict[str, GiveawayCommandHandler], request.app.state.giveaway_command_handlers)
    handler = handlers.get(identity.twitch_user_id)
    if handler is not None:
        handler.set_prefix(prefix)
    return {"command_prefix": prefix}
