"""Version-specific workaround for TwitchIO cancelling its own keepalive close."""

import asyncio
from functools import wraps
from importlib.metadata import version

from twitchio.eventsub.websockets import Websocket

SUPPORTED_TWITCHIO_VERSION = "3.3.2"
_PATCH_MARKER = "_overlays_keepalive_close_fix_332"


def install_twitchio_keepalive_close_fix() -> None:
    """Install once per process; revalidate/remove this shim when TwitchIO changes."""
    if version("twitchio") != SUPPORTED_TWITCHIO_VERSION:
        raise RuntimeError(
            "The TwitchIO keepalive close workaround requires TwitchIO 3.3.2; "
            "revalidate it before changing the dependency."
        )

    original_close = Websocket.close
    if getattr(original_close, _PATCH_MARKER, False):
        return

    @wraps(original_close)
    async def close(
        self: Websocket, cleanup: bool = True, *, reassociate: bool = True
    ) -> None:
        if (
            self._keep_alive_task is not None
            and self._keep_alive_task is asyncio.current_task()
        ):
            # The expired keepalive will return after closing. Do not let upstream
            # cancel that same task before its awaited transport cleanup finishes.
            self._keep_alive_task = None
        await original_close(self, cleanup=cleanup, reassociate=reassociate)

    setattr(close, _PATCH_MARKER, True)
    Websocket.close = close
