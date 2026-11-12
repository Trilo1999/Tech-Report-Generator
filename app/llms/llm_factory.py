from functools import lru_cache
from typing import Any, Optional

from app.config.env_config import settings
from app.config.log_config import logger


@lru_cache(maxsize=16)
def get_cached_chat_client(
    provider: str,
    model_name: str,
    temperature: float,
    request_timeout: float,
    max_retries: int,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Any:
    """Instantiate and cache a chat client instance with configured timeouts and retries.

    Args:
        provider: 'hive', 'google', or 'openai'.
        model_name: Name of the LLM model.
        temperature: Generation temperature.
        request_timeout: Network call timeout in seconds.
        max_retries: Number of exponential backoff retries.
        base_url: Optional base URL for OpenAI-compatible proxies.
        api_key: API secret key.

    Returns:
        Configured LLM chat client.
    """
    logger.debug(
        "Creating cached LLM client for provider=%s model=%s timeout=%.1fs retries=%d",
        provider,
        model_name,
        request_timeout,
        max_retries,
    )

    if provider == "hive":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key or settings.HIVE_SECRET_KEY,
            base_url=base_url or settings.HIVE_BASE_URL,
            request_timeout=request_timeout,
            max_retries=max_retries,
        )

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key or settings.GEMINI_API_KEY,
            timeout=request_timeout,
            max_retries=max_retries,
            include_thoughts=True,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key or settings.OPENAI_API_KEY,
            request_timeout=request_timeout,
            max_retries=max_retries,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")


def get_default_chat_client() -> Any:
    """Return the default chat client based on available keys and configuration.

    Selection order: HIVE > GEMINI > OPENAI (first non-empty key wins).
    Utilizes LRU client caching and configured timeouts/retries.

    Returns:
        Chat model client (ChatOpenAI or ChatGoogleGenerativeAI).

    Raises:
        ValueError: If neither HIVE_SECRET_KEY, OPENAI_API_KEY, nor GEMINI_API_KEY is set.
    """
    timeout = getattr(settings, "LLM_REQUEST_TIMEOUT", 60.0)
    retries = getattr(settings, "LLM_MAX_RETRIES", 3)

    if settings.HIVE_SECRET_KEY and settings.HIVE_SECRET_KEY.strip() not in (
        "",
        "your-hive-secret-key-here",
    ):
        return get_cached_chat_client(
            provider="hive",
            model_name=settings.HIVE_MODEL_NAME,
            temperature=0.1,
            request_timeout=timeout,
            max_retries=retries,
            base_url=settings.HIVE_BASE_URL,
            api_key=settings.HIVE_SECRET_KEY,
        )

    elif settings.GEMINI_API_KEY:
        from app.constants.app_constants import GEMINI_CHAT_MODEL

        return get_cached_chat_client(
            provider="google",
            model_name=GEMINI_CHAT_MODEL.MODEL_NAME.value,
            temperature=GEMINI_CHAT_MODEL.TEMPERATURE.value,
            request_timeout=timeout,
            max_retries=retries,
            api_key=settings.GEMINI_API_KEY,
        )

    elif settings.OPENAI_API_KEY:
        from app.constants.app_constants import OPENAI_CHAT_MODEL

        return get_cached_chat_client(
            provider="openai",
            model_name=OPENAI_CHAT_MODEL.MODEL_NAME.value,
            temperature=OPENAI_CHAT_MODEL.TEMPERATURE.value,
            request_timeout=timeout,
            max_retries=retries,
            api_key=settings.OPENAI_API_KEY,
        )

    else:
        raise ValueError(
            "No LLM provider configured. Set HIVE_SECRET_KEY, OPENAI_API_KEY, or GEMINI_API_KEY"
        )


def clear_llm_client_cache() -> None:
    """Clear cached LLM client instances."""
    get_cached_chat_client.cache_clear()
