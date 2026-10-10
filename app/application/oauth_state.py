from secrets import compare_digest, token_urlsafe
from threading import Lock
from time import monotonic
from typing import Literal

OAuthFlow = Literal["bot", "streamer"]
OAUTH_STATE_TTL_SECONDS = 600


class OAuthStateStore:
    def __init__(self, ttl_seconds: float = OAUTH_STATE_TTL_SECONDS) -> None:
        if ttl_seconds <= 0:
            raise ValueError("The Oauth state TTL must be positive")

        self._ttl_seconds = ttl_seconds
        self._states: dict[str, tuple[float, OAuthFlow, str]] = {}
        self._lock = Lock()

    def issue(self, flow: OAuthFlow) -> tuple[str, str]:
        now = monotonic()

        with self._lock:
            self._remove_expired(now)

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
        expired_states = [
            state
            for state, (expires_at, _, _) in self._states.items()
            if expires_at <= now
        ]

        for state in expired_states:
            del self._states[state]
