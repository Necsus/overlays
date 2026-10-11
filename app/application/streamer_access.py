import asyncio
import logging

from app.application.session import SessionSigner
from app.domain.streamer import Streamer
from app.infrastructure.database import Database
from app.infrastructure.streamers import load_enabled_streamer_ids, load_streamer
from app.web.websocket import OverlayConnectionManager

STREAMER_ACCESS_POLL_SECONDS = 5
LOGGER = logging.getLogger("uvicorn.error")


class StreamerAccessGuard:
    """Enforce web/OBS access without changing chat, giveaways or their timers."""

    def __init__(
        self,
        database: Database,
        session_signer: SessionSigner,
        connections: OverlayConnectionManager,
    ) -> None:
        self._database = database
        self._session_signer = session_signer
        self._connections = connections

    async def load_streamer(self, streamer_id: str) -> Streamer | None:
        detached = []
        try:
            async with self._database.access_lock:
                streamer = await load_streamer(self._database, streamer_id)
                if streamer is None:
                    self._session_signer.revoke_streamer(streamer_id)
                    detached = self._connections.detach_streamer(streamer_id)
        finally:
            await self._connections.close_connections(detached)
        return streamer

    async def revoke_streamer(self, streamer_id: str) -> None:
        async with self._database.access_lock:
            self._session_signer.revoke_streamer(streamer_id)
            detached = self._connections.detach_streamer(streamer_id)
        await self._connections.close_connections(detached)

    async def reconcile(self) -> None:
        detached = []
        try:
            async with self._database.access_lock:
                # The session and socket quotas bound both this set and the SQL array.
                owners = self._session_signer.streamer_ids() | self._connections.streamer_ids()
                if owners:
                    enabled = await load_enabled_streamer_ids(self._database, sorted(owners))
                    for streamer_id in owners - enabled:
                        self._session_signer.revoke_streamer(streamer_id)
                        detached.extend(self._connections.detach_streamer(streamer_id))
        finally:
            await self._connections.close_connections(detached)

    async def _close_unverified_connections(self) -> None:
        detached = []
        async with self._database.access_lock:
            for streamer_id in self._connections.streamer_ids():
                detached.extend(self._connections.detach_streamer(streamer_id))
        # A failed access check is not proof that the user's session was revoked.
        await self._connections.close_connections(detached, code=1011)

    async def run(self) -> None:
        while True:
            try:
                await self.reconcile()
            except Exception as error:
                LOGGER.warning("Unable to verify streamer access: error=%s", type(error).__name__)
                await self._close_unverified_connections()
            await asyncio.sleep(STREAMER_ACCESS_POLL_SECONDS)
