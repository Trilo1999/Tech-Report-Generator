import logging
from typing import Optional

try:
    from redis import Redis
except ImportError:
    Redis = None

from app.config.env_config import settings

logger = logging.getLogger("research_agent.redis")

_REDIS_AVAILABLE: Optional[bool] = None


class RedisConfig:
    """Provide Redis connection details and helpers."""

    def __init__(self) -> None:
        """Initialize Redis config from environment settings."""
        self.host = settings.REDIS_HOST
        self.port = int((settings.REDIS_PORT or "6379").strip() or "6379")
        self.db = int((settings.REDIS_DB or "0").strip() or "0")
        self.password = getattr(settings, "REDIS_PASSWORD", None)

    def get_redis_client(self, socket_timeout: float = 2.0) -> Optional["Redis"]:
        """Create and return a Redis client with configured socket timeouts.

        Returns:
            Redis client instance with decode_responses enabled, or None if disabled/unavailable.
        """
        if Redis is None or not settings.USE_REDIS:
            return None
        try:
            url = self.get_redis_url()
            return Redis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=socket_timeout,
                socket_timeout=socket_timeout,
            )
        except Exception as e:
            logger.debug("Failed to create Redis client from url: %s", e)
            return None

    def get_redis_url(self) -> str:
        """Return Redis URL string.

        Returns:
            Redis connection URL (e.g., redis://host:port/db or redis://:pass@host:port/db).
        """
        if getattr(settings, "REDIS_URL", None):
            return settings.REDIS_URL

        scheme = (settings.REDIS_PROTOCOL or "redis").lower()
        if scheme in {"http", "https"}:
            scheme = "redis"

        if self.password:
            return f"{scheme}://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"{scheme}://{self.host}:{self.port}/{self.db}"

    def is_available(self, force_check: bool = False) -> bool:
        """Check if Redis server is reachable via ping.

        Args:
            force_check: Whether to ignore cached status and re-ping the server.

        Returns:
            True if Redis responded to ping, False otherwise.
        """
        global _REDIS_AVAILABLE
        if not settings.USE_REDIS or Redis is None:
            return False

        if _REDIS_AVAILABLE is not None and not force_check:
            return _REDIS_AVAILABLE

        try:
            client = self.get_redis_client(socket_timeout=1.0)
            if client is None:
                _REDIS_AVAILABLE = False
                return False
            client.ping()
            _REDIS_AVAILABLE = True
            return True
        except Exception as e:
            logger.debug("Redis ping check failed (%s); fallback mode enabled.", e)
            _REDIS_AVAILABLE = False
            return False


redis_config = RedisConfig()


def is_redis_available() -> bool:
    """Return whether Redis is reachable and available."""
    return redis_config.is_available()


def reset_redis_status() -> None:
    """Reset cached Redis availability status to force a live check on next query."""
    global _REDIS_AVAILABLE
    _REDIS_AVAILABLE = None
