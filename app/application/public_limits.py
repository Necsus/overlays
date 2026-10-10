from threading import Lock
from time import monotonic

PUBLIC_REQUEST_WINDOW_SECONDS = 60


class PublicRequestBudget:
    """Fixed-window admission budget with a bounded map of client counters."""

    def __init__(self, max_requests: int, max_per_client: int) -> None:
        if max_requests <= 0 or not 0 < max_per_client <= max_requests:
            raise ValueError("Request budgets must be positive and ordered")
        self._max_requests = max_requests
        self._max_per_client = max_per_client
        self._window_started_at = monotonic()
        self._total = 0
        self._clients: dict[str, int] = {}
        self._lock = Lock()

    def allow(self, client_id: str) -> bool:
        with self._lock:
            now = monotonic()
            if now - self._window_started_at >= PUBLIC_REQUEST_WINDOW_SECONDS:
                self._window_started_at = now
                self._total = 0
                self._clients.clear()

            count = self._clients.get(client_id, 0)
            if self._total >= self._max_requests or count >= self._max_per_client:
                return False

            # Only admitted clients are stored, so the global budget bounds memory.
            self._clients[client_id] = count + 1
            self._total += 1
            return True
