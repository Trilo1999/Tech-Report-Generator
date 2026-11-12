"""Unit tests for LLM client caching, configurable timeouts, and retry policies."""

from app.config.env_config import settings
from app.llms.llm_factory import clear_llm_client_cache, get_cached_chat_client
from app.llms.openai_chat_client import OpenAIChatClient


def test_llm_settings_configuration():
    """Verify default LLM resilience settings are present."""
    assert hasattr(settings, "LLM_REQUEST_TIMEOUT")
    assert settings.LLM_REQUEST_TIMEOUT > 0
    assert hasattr(settings, "LLM_MAX_RETRIES")
    assert settings.LLM_MAX_RETRIES >= 1
    assert hasattr(settings, "LLM_CLIENT_CACHE_MAX_SIZE")


def test_openai_chat_client_timeout_and_retries():
    """Verify OpenAIChatClient propagates request_timeout and max_retries."""
    factory = OpenAIChatClient()
    client = factory.create_client()
    assert client.request_timeout == settings.LLM_REQUEST_TIMEOUT
    assert client.max_retries == settings.LLM_MAX_RETRIES


def test_cached_chat_client_memoization():
    """Verify repeated calls with identical parameters return the cached client instance."""
    clear_llm_client_cache()

    client1 = get_cached_chat_client(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.2,
        request_timeout=45.0,
        max_retries=2,
        api_key="test-key-mock",
    )
    client2 = get_cached_chat_client(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.2,
        request_timeout=45.0,
        max_retries=2,
        api_key="test-key-mock",
    )

    assert client1 is client2

    # Different parameter returns new client
    client3 = get_cached_chat_client(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.7,
        request_timeout=45.0,
        max_retries=2,
        api_key="test-key-mock",
    )
    assert client1 is not client3


def test_clear_llm_client_cache():
    """Verify cache clear resets memoized instances."""
    clear_llm_client_cache()
    client1 = get_cached_chat_client(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.1,
        request_timeout=30.0,
        max_retries=1,
        api_key="test-key-mock",
    )
    clear_llm_client_cache()
    client2 = get_cached_chat_client(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.1,
        request_timeout=30.0,
        max_retries=1,
        api_key="test-key-mock",
    )
    assert client1 is not client2
