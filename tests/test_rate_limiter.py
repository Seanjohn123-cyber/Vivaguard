import unittest

from app.rate_limiter import RateLimiter, TokenBucket


class TokenBucketTests(unittest.TestCase):
    def test_bucket_consumes_when_tokens_available(self):
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        bucket.tokens = 10

        self.assertTrue(bucket.consume(5))
        self.assertEqual(bucket.tokens, 5)

    def test_bucket_rejects_when_tokens_missing(self):
        bucket = TokenBucket(capacity=10, refill_rate=0.0)
        bucket.tokens = 2

        self.assertFalse(bucket.consume(5))


class RateLimiterTests(unittest.TestCase):
    def test_session_allows_requests_within_limit(self):
        limiter = RateLimiter(max_requests_per_minute=3, tokens_per_request=1, token_bucket_capacity=10, token_bucket_refill_rate=5)

        self.assertTrue(limiter.allow("session-1"))
        self.assertTrue(limiter.allow("session-1"))
        self.assertTrue(limiter.allow("session-1"))

    def test_session_blocks_after_limit(self):
        limiter = RateLimiter(max_requests_per_minute=2, tokens_per_request=1, token_bucket_capacity=10, token_bucket_refill_rate=5)

        self.assertTrue(limiter.allow("session-2"))
        self.assertTrue(limiter.allow("session-2"))
        self.assertFalse(limiter.allow("session-2"))


if __name__ == "__main__":
    unittest.main()
