import time
from collections import defaultdict, deque


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self, amount: float = 1.0) -> bool:
        self._refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False


class RateLimiter:
    def __init__(
        self,
        max_requests_per_minute: int = 60,
        tokens_per_request: int = 1,
        token_bucket_capacity: int = 50,
        token_bucket_refill_rate: float = 5.0,
    ) -> None:
        self.max_requests_per_minute = max_requests_per_minute
        self.tokens_per_request = tokens_per_request
        self._request_windows: dict[str, deque[float]] = defaultdict(deque)
        self._token_buckets: dict[str, TokenBucket] = {}
        self._bucket_capacity = token_bucket_capacity
        self._bucket_refill_rate = token_bucket_refill_rate

    def _get_bucket(self, session_id: str) -> TokenBucket:
        bucket = self._token_buckets.get(session_id)
        if bucket is None:
            bucket = TokenBucket(self._bucket_capacity, self._bucket_refill_rate)
            self._token_buckets[session_id] = bucket
        return bucket

    def allow(self, session_id: str, tokens: int | None = None) -> bool:
        requested_tokens = self.tokens_per_request if tokens is None else tokens
        bucket = self._get_bucket(session_id)

        if not bucket.consume(requested_tokens):
            return False

        now = time.monotonic()
        window = self._request_windows[session_id]
        window.append(now)

        cutoff = now - 60
        while window and window[0] <= cutoff:
            window.popleft()

        if len(window) > self.max_requests_per_minute:
            window.pop()
            return False

        return True
