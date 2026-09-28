import asyncio
import logging
from collections.abc import Awaitable
from contextlib import suppress
from copy import copy
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from app.domain.giveaway import GiveawayEngine, GiveawayState, Participant
from app.infrastructure.database import Database
from app.infrastructure.history import (
    add_participant,
    create_giveaway,
    draw_giveaway,
    open_giveaway,
    restore_active_giveaway,
    stop_giveaway,
)
from app.web.websocket import OverlayConnectionManager

T = TypeVar("T")


class GiveawayService:
    def __init__(
        self,
        streamer_id: str,
        engine: GiveawayEngine,
        database: Database,
        overlay_connections: OverlayConnectionManager,
    ) -> None:
        self._streamer_id = streamer_id
        self._engine = engine
        self._database = database
        self._overlay_connections = overlay_connections
        self._lock = asyncio.Lock()
        self._timer: asyncio.Task[None] | None = None
        self._needs_reload = False

    async def _persist(self, operation: Awaitable[T]) -> T:
        try:
            return await operation
        except BaseException:
            # A lost connection during COMMIT can mean the write succeeded.
            # Reload before another mutation instead of replaying it blindly.
            self._needs_reload = True
            raise

    async def _ensure_consistent(self) -> None:
        if not self._needs_reload:
            return
        restored = GiveawayEngine()
        await restore_active_giveaway(self._database, self._streamer_id, restored)
        self._cancel_timer()
        self._apply(restored)
        self._needs_reload = False
        self.resume_timer()
        await self._broadcast_state()

    def _apply(self, engine: GiveawayEngine) -> None:
        self._engine.state = engine.state
        self._engine.giveaway_id = engine.giveaway_id
        self._engine.lot = engine.lot
        self._engine.closes_at = engine.closes_at
        self._engine.participants = engine.participants
        self._engine.winners = engine.winners

    def resume_timer(self) -> None:
        if self._engine.closes_at is not None and (
            self._timer is None or self._timer.done()
        ):
            self._timer = asyncio.create_task(
                self._run_timer(), name="giveaway-deadline"
            )

    async def close(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            with suppress(asyncio.CancelledError):
                await self._timer
            self._timer = None

    def _cancel_timer(self) -> None:
        if self._timer is asyncio.current_task():
            return
        if self._timer is not None:
            self._timer.cancel()
        self._timer = None

    async def _run_timer(self) -> None:
        while self._engine.closes_at is not None:
            delay = (self._engine.closes_at - datetime.now(UTC)).total_seconds()
            await asyncio.sleep(max(0, delay))
            try:
                async with self._lock:
                    await self._expire_if_due()
            except Exception:
                logging.getLogger("uvicorn.error").exception("Giveaway deadline failed")
                await asyncio.sleep(1)

    async def _expire_if_due(self) -> None:
        await self._ensure_consistent()
        deadline = self._engine.closes_at
        if deadline is None or datetime.now(UTC) < deadline:
            return
        giveaway_id = self._active_giveaway_id()
        if self._engine.participants:
            await self._draw(giveaway_id)
        else:
            await self._persist(
                stop_giveaway(self._database, self._streamer_id, giveaway_id)
            )
            self._engine.stop()
        self._cancel_timer()
        await self._broadcast_state()

    async def _draw(self, giveaway_id: str) -> Participant:
        candidate = copy(self._engine)
        candidate.winners = self._engine.winners.copy()
        winner = candidate.pull()
        await self._persist(draw_giveaway(self._database, self._streamer_id, giveaway_id, winner))
        self._apply(candidate)
        return winner

    async def set_lot(self, lot: str) -> None:
        async with self._lock:
            await self._ensure_consistent()
            if self._engine.state is not GiveawayState.HIDDEN:
                raise RuntimeError("A giveaway is already active")
            candidate = GiveawayEngine()
            candidate.set_lot(lot)
            if candidate.giveaway_id is None or candidate.lot is None:
                raise RuntimeError("The giveaway was not initialized correctly")
            await self._persist(
                create_giveaway(self._database, self._streamer_id, candidate.giveaway_id, candidate.lot)
            )
            self._apply(candidate)
            await self._broadcast_state()

    async def start(self, duration_seconds: int | None = None) -> None:
        if duration_seconds is not None and (
            type(duration_seconds) is not int or not 1 <= duration_seconds <= 604800
        ):
            raise ValueError("Duration must be between 1 and 604800 seconds")
        async with self._lock:
            await self._ensure_consistent()
            giveaway_id = self._active_giveaway_id()
            if self._engine.state is not GiveawayState.WAITING:
                raise RuntimeError("A giveaway is not waiting")
            deadline = (
                datetime.now(UTC) + timedelta(seconds=duration_seconds)
                if duration_seconds is not None
                else None
            )
            await self._persist(open_giveaway(self._database, self._streamer_id, giveaway_id, deadline))
            self._engine.start()
            self._engine.closes_at = deadline
            self.resume_timer()
            await self._broadcast_state()

    async def join(self, participant: Participant) -> bool:
        async with self._lock:
            await self._expire_if_due()
            giveaway_id = self._active_giveaway_id()
            if self._engine.state is not GiveawayState.OPEN:
                raise RuntimeError("The giveaway is not open")
            if any(
                p.twitch_user_id == participant.twitch_user_id
                for p in self._engine.participants
            ):
                return False
            was_persisted = await self._persist(
                add_participant(self._database, self._streamer_id, giveaway_id, participant)
            )
            if not was_persisted:
                self._needs_reload = True
                await self._ensure_consistent()
                return False
            self._engine.join(participant)
            await self._broadcast_state()
            return True

    async def pull(self) -> Participant:
        async with self._lock:
            await self._ensure_consistent()
            giveaway_id = self._active_giveaway_id()
            winner = await self._draw(giveaway_id)
            self._cancel_timer()
            await self._broadcast_state()
            return winner

    async def stop(self) -> None:
        async with self._lock:
            await self._ensure_consistent()
            giveaway_id = self._active_giveaway_id()
            await self._persist(
                stop_giveaway(self._database, self._streamer_id, giveaway_id)
            )
            self._engine.stop()
            self._cancel_timer()
            await self._broadcast_state()

    def _active_giveaway_id(self) -> str:
        if self._engine.giveaway_id is None:
            raise RuntimeError("There is no active giveaway")
        return self._engine.giveaway_id

    async def _broadcast_state(self) -> None:
        await self._overlay_connections.broadcast(
            self._streamer_id, self._engine.overlay_snapshot()
        )
