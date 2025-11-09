"""Unit tests for rate limiter"""
import pytest
import fakeredis.aioredis
from src.bot.rate_limiter import RateLimiter


@pytest.fixture
async def redis_client():
    """Fixture for fake Redis client"""
    client = fakeredis.aioredis.FakeRedis(decode_responses=False)
    yield client
    await client.close()


@pytest.fixture
def rate_limiter(redis_client):
    """Fixture for RateLimiter"""
    return RateLimiter(redis_client, max_messages=5, window=60)


@pytest.mark.asyncio
async def test_rate_limit_allows_within_limit(rate_limiter):
    """Test rate limiter allows requests within limit"""
    user_id = 12345

    # First 5 requests should be allowed
    for i in range(5):
        result = await rate_limiter.check_rate_limit(user_id)
        assert result is True


@pytest.mark.asyncio
async def test_rate_limit_blocks_over_limit(rate_limiter):
    """Test rate limiter blocks requests over limit"""
    user_id = 12345

    # First 5 requests should be allowed
    for i in range(5):
        await rate_limiter.check_rate_limit(user_id)

    # 6th request should be blocked
    result = await rate_limiter.check_rate_limit(user_id)
    assert result is False


@pytest.mark.asyncio
async def test_rate_limit_per_user(rate_limiter):
    """Test rate limiter is applied per user"""
    user1 = 111
    user2 = 222

    # User 1 maxes out limit
    for i in range(5):
        await rate_limiter.check_rate_limit(user1)

    # User 2 should still be allowed
    result = await rate_limiter.check_rate_limit(user2)
    assert result is True
