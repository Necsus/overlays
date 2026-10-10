from secrets import compare_digest, token_urlsafe
from threading import Lock
from time import monotonic
from typing import Literal

from app.application.public_limits import PublicRequestBudget

OAuthFlow = Literal["bot", "streamer"]
OAUTH_STATE_TTL_SECONDS = 600
MAX_PENDING_OAUTH_STATES = 512


class OAuthStateLimitError(RuntimeError):
    """Admission refused without discarding an existing OAuth transaction."""


class OAuthStateStore:
    def __init__(
        self,
        ttl_seconds: float = OAUTH_STATE_TTL_SECONDS,
        max_pending_states: int = MAX_PENDING_OAUTH_STATES,
    ) -> None:
        if ttl_seconds <= 0 or max_pending_states <= 0:
            raise ValueError("OAuth TTL and capacity must be positive")

        self._ttl_seconds = ttl_seconds
        self._max_pending_states = max_pending_states
        self._request_budget = PublicRequestBudget(max_requests=60, max_per_client=10)
        self._states: dict[str, tuple[float, OAuthFlow, str]] = {}
        self._lock = Lock()

    def issue(self, flow: OAuthFlow, client_id: str) -> tuple[str, str]:
        with self._lock:
            if not self._request_budget.allow(client_id):
                raise OAuthStateLimitError("OAuth request budget exhausted")
            now = monotonic()
            self._remove_expired(now)
            if len(self._states) >= self._max_pending_states:
                raise OAuthStateLimitError("OAuth transaction capacity exhausted")

            state = token_urlsafe(32)
            while state in self._states:
                state = token_urlsafe(32)

            browser_token = token_urlsafe(32)
            self._states[state] = (now + self._ttl_seconds, flow, browser_token)

        return state, browser_token

    def consume(self, state: str, browser_token: str | None) -> OAuthFlow | None:
        if browser_token is None or not browser_token.isascii():
            return None

        with self._lock:
            state_data = self._states.get(state)
            if state_data is None:
                return None

            expires_at, flow, expected_browser_token = state_data
            if expires_at <= monotonic():
                del self._states[state]
                return None

            # A callback in another browser must not invalidate the original flow.
            if not compare_digest(browser_token, expected_browser_token):
                return None

            del self._states[state]
            return flow

    def _remove_expired(self, now: float) -> None:
        # Issuance is serialized with a fixed TTL, so insertion order is expiry order.
        while self._states:
            state = next(iter(self._states))
            expires_at, _, _ = self._states[state]
            if expires_at > now:
                break
            del self._states[state]
