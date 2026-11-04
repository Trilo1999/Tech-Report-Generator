import logging
from typing import Any, Dict, List, Optional

from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.config.env_config import settings
from app.config.redis_config import is_redis_available, redis_config
from app.utils.core_utils.in_memory_utils import in_memory_history

logger = logging.getLogger("research_agent.chat_memory")


class ResilientChatMessageHistory(BaseChatMessageHistory):
    """Resilient chat message history that delegates to Redis with TTL when available,
    transparently falling back to in-memory store if Redis is unavailable or disconnected.
    """

    def __init__(
        self,
        session_id: str,
        redis_url: str,
        key_prefix: str = "agent_chat:",
        ttl: int = 86400,
    ) -> None:
        self.session_id = session_id
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl = ttl
        self._redis_impl: Optional[RedisChatMessageHistory] = None

    def _get_redis_impl(self) -> Optional[RedisChatMessageHistory]:
        if not is_redis_available():
            return None
        if self._redis_impl is None:
            try:
                self._redis_impl = RedisChatMessageHistory(
                    session_id=self.session_id,
                    url=self.redis_url,
                    key_prefix=self.key_prefix,
                    ttl=self.ttl,
                )
            except Exception as e:
                logger.warning(
                    "Could not initialize RedisChatMessageHistory for session %s: %s",
                    self.session_id,
                    e,
                )
                return None
        return self._redis_impl

    @property
    def messages(self) -> List[BaseMessage]:
        """Fetch messages from Redis if reachable, else fall back to in-memory store."""
        redis_impl = self._get_redis_impl()
        if redis_impl is not None:
            try:
                return redis_impl.messages
            except Exception as e:
                logger.warning(
                    "Redis error fetching messages for session %s: %s; falling back to in-memory",
                    self.session_id,
                    e,
                )
        return in_memory_history.get_history(self.session_id).messages

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to Redis if reachable, else save to in-memory store."""
        redis_impl = self._get_redis_impl()
        if redis_impl is not None:
            try:
                redis_impl.add_message(message)
                return
            except Exception as e:
                logger.warning(
                    "Redis error writing message for session %s: %s; falling back to in-memory",
                    self.session_id,
                    e,
                )
        in_memory_history.get_history(self.session_id).add_message(message)

    def clear(self) -> None:
        """Clear session messages from Redis and in-memory store."""
        redis_impl = self._get_redis_impl()
        if redis_impl is not None:
            try:
                redis_impl.clear()
            except Exception as e:
                logger.warning(
                    "Redis error clearing session %s: %s", self.session_id, e
                )
        in_memory_history.get_history(self.session_id).clear()


class RedisHistory:
    """Provide Redis-backed conversation memory with fallback, TTL, and inspection helpers."""

    def __init__(self) -> None:
        """Initialize Redis history from config."""
        self.redis_config = redis_config

    @property
    def redis_url(self) -> str:
        return self.redis_config.get_redis_url()

    def get_redis_history(
        self,
        session_id: str,
        key_prefix: str = "agent_chat:",
        ttl: Optional[int] = None,
    ) -> BaseChatMessageHistory:
        """Create a resilient chat history store for a session.

        Args:
            session_id: Unique identifier for the conversation session.
            key_prefix: Redis key prefix. Defaults to "agent_chat:".
            ttl: Time-to-live for history entries in seconds.

        Returns:
            ResilientChatMessageHistory instance for the session.
        """
        effective_ttl = ttl or getattr(settings, "REDIS_CHAT_TTL_SECONDS", 86400)
        return ResilientChatMessageHistory(
            session_id=session_id,
            redis_url=self.redis_url,
            key_prefix=key_prefix,
            ttl=effective_ttl,
        )

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve serializable conversation messages for a session.

        Args:
            session_id: Conversation session identifier.

        Returns:
            List of dictionaries with 'role' and 'content'.
        """
        history = self.get_redis_history(session_id)
        result: List[Dict[str, Any]] = []
        for msg in history.messages:
            role = "user"
            if isinstance(msg, AIMessage):
                role = "assistant"
            elif isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, HumanMessage):
                role = "user"
            elif hasattr(msg, "type"):
                role = "assistant" if msg.type == "ai" else msg.type
            result.append({"role": role, "content": msg.content})
        return result

    def clear_history(self, session_id: str) -> bool:
        """Clear conversation history for a session from all stores.

        Args:
            session_id: Conversation session identifier.

        Returns:
            True if cleared successfully.
        """
        history = self.get_redis_history(session_id)
        history.clear()
        return True

    def get_backend(self) -> str:
        """Return the active storage backend name ('redis' or 'in_memory')."""
        return "redis" if is_redis_available() else "in_memory"


redis_history = RedisHistory()
