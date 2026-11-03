from app.config.env_config import settings


def get_default_chat_client():
    """Return the default chat client based on available keys.

    Selection order: HIVE > GEMINI > OPENAI (first non-empty key wins).

    Returns:
        Chat model client (ChatOpenAI or ChatGoogleGenerativeAI).

    Raises:
        ValueError: If neither HIVE_SECRET_KEY, OPENAI_API_KEY, nor GEMINI_API_KEY is set.
    """
    if settings.HIVE_SECRET_KEY and settings.HIVE_SECRET_KEY.strip() not in (
        "",
        "your-hive-secret-key-here",
    ):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.HIVE_MODEL_NAME,
            temperature=0.1,
            api_key=settings.HIVE_SECRET_KEY,
            base_url=settings.HIVE_BASE_URL,
        )

    elif settings.GEMINI_API_KEY:
        from app.llms.gemini_chat_client import default_chat_client

        return default_chat_client

    elif settings.OPENAI_API_KEY:
        from app.llms.openai_chat_client import default_chat_client

        return default_chat_client

    else:
        raise ValueError(
            "No LLM provider configured. Set HIVE_SECRET_KEY, OPENAI_API_KEY, or GEMINI_API_KEY"
        )
