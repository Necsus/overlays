import secrets
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import cast

from itsdangerous import BadSignature, URLSafeTimedSerializer

SESSION_SALT = "giveaway-admin-session-v2"
SESSION_COOKIE_NAME = "giveaway_session"
MAX_ACTIVE_SESSIONS = 4096
MAX_ACTIVE_SESSIONS_PER_STREAMER = 32
MAX_SESSION_COOKIE_CHARACTERS = 1024


@dataclass(frozen=True)
class SessionIdentity:
    twitch_user_id: str


@dataclass(frozen=True)
class _ActiveSession:
    twitch_user_id: str
    expires_at: float


class SessionCapacityError(RuntimeError):
    """Session admission failed without evicting another user's session."""


class SessionSigner:
    def __init__(
        self,
        secret_key: str,
        max_age_seconds: int,
        max_sessions: int = MAX_ACTIVE_SESSIONS,
        clock: Callable[[], float] = monotonic,
        max_sessions_per_streamer: int = MAX_ACTIVE_SESSIONS_PER_STREAMER,
    ) -> None:
        if not secret_key.strip():
            raise ValueError("The session secret cannot be empty")
        if max_age_seconds <= 0:
            raise ValueError("The session maximum age must be positive")
        if min(max_sessions, max_sessions_per_streamer) <= 0:
            raise ValueError("The session capacities must be positive")

        self._serializer = URLSafeTimedSerializer(
            secret_key=secret_key,
            salt=SESSION_SALT,
        )
        self._max_age_seconds = max_age_seconds
        self._max_sessions = max_sessions
        self._max_sessions_per_streamer = max_sessions_per_streamer
        self._clock = clock
        self._sessions: OrderedDict[str, _ActiveSession] = OrderedDict()
        # Logout can run in FastAPI's thread pool; verification and issuance share this lock.
        self._lock = threading.Lock()

    def _purge_expired(self, now: float) -> None:
        # A fixed TTL and monotonic clock keep insertion order equal to expiry order.
        while self._sessions:
            session_id = next(iter(self._sessions))
            if self._sessions[session_id].expires_at > now:
                break
            self._sessions.popitem(last=False)

    def create(self, twitch_user_id: str) -> str:
        if not twitch_user_id.strip():
            raise ValueError("The Twitch user ID cannot be empty")

        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            if (
                len(self._sessions) >= self._max_sessions
                or sum(
                    session.twitch_user_id == twitch_user_id
                    for session in self._sessions.values()
                ) >= self._max_sessions_per_streamer
            ):
                raise SessionCapacityError("The session capacity is exhausted")
            session_id = secrets.token_urlsafe(32)
            while session_id in self._sessions:
                session_id = secrets.token_urlsafe(32)
            cookie_value = self._serializer.dumps(
                {"twitch_user_id": twitch_user_id, "session_id": session_id}
            )
            self._sessions[session_id] = _ActiveSession(
                twitch_user_id=twitch_user_id,
                expires_at=now + self._max_age_seconds,
            )
            return cookie_value

    def _read_cookie(self, cookie_value: str) -> tuple[str, str] | None:
        if len(cookie_value) > MAX_SESSION_COOKIE_CHARACTERS:
            return None
        try:
            raw_payload: object = self._serializer.loads(
                cookie_value,
                max_age=self._max_age_seconds,
            )
        except BadSignature:
            return None
        if not isinstance(raw_payload, dict):
            return None
        payload = cast(dict[object, object], raw_payload)
        if set(payload) != {"twitch_user_id", "session_id"}:
            return None
        twitch_user_id = payload.get("twitch_user_id")
        session_id = payload.get("session_id")
        if (
            not isinstance(twitch_user_id, str)
            or not twitch_user_id.strip()
            or not isinstance(session_id, str)
            or not session_id
        ):
            return None
        return twitch_user_id, session_id

    def verify(self, cookie_value: str) -> SessionIdentity | None:
        payload = self._read_cookie(cookie_value)
        if payload is None:
            return None
        twitch_user_id, session_id = payload
        with self._lock:
            self._purge_expired(self._clock())
            session = self._sessions.get(session_id)
            if session is None or session.twitch_user_id != twitch_user_id:
                return None
            return SessionIdentity(twitch_user_id=twitch_user_id)

    def revoke(self, cookie_value: str) -> None:
        payload = self._read_cookie(cookie_value)
        if payload is None:
            return
        twitch_user_id, session_id = payload
        with self._lock:
            self._purge_expired(self._clock())
            session = self._sessions.get(session_id)
            if session is not None and session.twitch_user_id == twitch_user_id:
                self._sessions.pop(session_id)

    def revoke_streamer(self, twitch_user_id: str) -> None:
        with self._lock:
            self._purge_expired(self._clock())
            for session_id, session in list(self._sessions.items()):
                if session.twitch_user_id == twitch_user_id:
                    self._sessions.pop(session_id)

    def streamer_ids(self) -> set[str]:
        with self._lock:
            self._purge_expired(self._clock())
            return {session.twitch_user_id for session in self._sessions.values()}
