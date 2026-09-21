from app.core.config import settings
from app.services.assemblyai_client import AssemblyAIClient
from app.services.broker import SessionBroker
from app.services.rate_limiter import RateLimiter

broker = SessionBroker(
    rate_limiter=RateLimiter(
        max_requests_per_minute=settings.max_requests_per_minute,
        tokens_per_request=settings.tokens_per_request,
        token_bucket_capacity=settings.token_bucket_capacity,
        token_bucket_refill_rate=settings.token_bucket_refill_rate,
    )
)

assemblyai = AssemblyAIClient(
    api_key=settings.assemblyai_api_key,
    base_url=settings.assemblyai_realtime_url,
    sample_rate=settings.assemblyai_sample_rate,
)
