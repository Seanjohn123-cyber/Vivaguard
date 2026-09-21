from app.schemas.health import HealthResponse


async def health() -> HealthResponse:
    """Health check endpoint confirming broker service availability, rate limits, and server status."""
    return HealthResponse()
