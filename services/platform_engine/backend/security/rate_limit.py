from collections import defaultdict, deque
from time import monotonic

class SlidingWindowRateLimiter:
    def __init__(self, limit: int = 60, window_seconds: float = 60.0):
        self.limit, self.window = limit, window_seconds
        self._events = defaultdict(deque)
    def allow(self, key: str, now: float | None = None) -> bool:
        t = monotonic() if now is None else now
        q = self._events[key]
        while q and q[0] <= t - self.window: q.popleft()
        if len(q) >= self.limit: return False
        q.append(t); return True
