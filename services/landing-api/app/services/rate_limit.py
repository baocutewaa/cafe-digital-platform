from __future__ import annotations

import time
from collections import defaultdict, deque

from app.core.config import settings
from app.core.exceptions import RateLimitExceededError


class SlidingWindowRateLimiter:
    """In-memory per-session (8/min) and per-IP (30/min) sliding window limiter."""

    def __init__(
        self,
        session_limit: int | None = None,
        ip_limit: int = 30,
        window_seconds: float = 60.0,
    ) -> None:
        self.session_limit = session_limit or settings.CHAT_RATE_LIMIT_PER_MIN
        self.ip_limit = ip_limit
        self.window_seconds = window_seconds
        self._session_hits: dict[str, deque[float]] = defaultdict(deque)
        self._ip_hits: dict[str, deque[float]] = defaultdict(deque)

    def _prune_and_check(self, bucket: deque[float], limit: int, now: float) -> bool:
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True

    def check_and_record(self, session_key: str, ip_key: str) -> None:
        now = time.monotonic()
        if not self._prune_and_check(self._session_hits[session_key], self.session_limit, now):
            raise RateLimitExceededError(
                f"Bạn đã gửi quá {self.session_limit} tin nhắn/phút trong phiên này. "
                "Vui lòng đợi giây lát."
            )
        if ip_key and not self._prune_and_check(self._ip_hits[ip_key], self.ip_limit, now):
            raise RateLimitExceededError(
                "Hệ thống đang nhận nhiều yêu cầu từ địa chỉ của bạn. Vui lòng thử lại sau ít phút."
            )

    def reset(self) -> None:
        self._session_hits.clear()
        self._ip_hits.clear()


chat_rate_limiter = SlidingWindowRateLimiter()
