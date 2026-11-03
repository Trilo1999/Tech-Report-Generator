from app.config.env_config import settings
from app.utils.core_utils.in_memory_utils import in_memory_history


def get_message_history_factory():
    """Return the configured history factory for agent chat memory."""
    if settings.USE_REDIS:
        try:
            from app.utils.core_utils.redis_utils import redis_history

            return redis_history.get_redis_history
        except ImportError:
            pass
    return in_memory_history.get_history


message_history_factory = get_message_history_factory()
