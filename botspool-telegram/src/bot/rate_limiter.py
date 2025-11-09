"""Rate limiting for bot messages"""
import redis.asyncio as redis


class RateLimiter:
    """Redis-based rate limiter for user messages"""

    def __init__(
        self, redis_client: redis.Redis, max_messages: int = 5, window: int = 60
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Async Redis client
            max_messages: Maximum messages allowed per window
            window: Time window in seconds
        """
        self.redis = redis_client
        self.max_messages = max_messages
        self.window = window

    async def check_rate_limit(self, telegram_user_id: int) -> bool:
        """
        Check if user is within rate limit.

        Args:
            telegram_user_id: Telegram user ID

        Returns:
            True if within limit, False if exceeded
        """
        key = f"telegram:ratelimit:{telegram_user_id}"
        count = await self.redis.incr(key)

        if count == 1:
            await self.redis.expire(key, self.window)

        return count <= self.max_messages

    async def get_remaining_time(self, telegram_user_id: int) -> int:
        """
        Get seconds until rate limit resets.

        Args:
            telegram_user_id: Telegram user ID

        Returns:
            Seconds until reset (0 if no limit active)
        """
        key = f"telegram:ratelimit:{telegram_user_id}"
        ttl = await self.redis.ttl(key)
        return max(0, ttl)
