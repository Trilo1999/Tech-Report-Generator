from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config.env_config import settings
from app.constants.app_constants import GEMINI_CHAT_MODEL


class GeminiChatClient:
    """Factory for Gemini chat model clients."""

    def __init__(self) -> None:
        """Initialize with model name and temperature from constants."""
        self.model_name = GEMINI_CHAT_MODEL.MODEL_NAME.value
        self.temperature = GEMINI_CHAT_MODEL.TEMPERATURE.value
        self.timeout = getattr(settings, "LLM_REQUEST_TIMEOUT", 60.0)
        self.max_retries = getattr(settings, "LLM_MAX_RETRIES", 3)

    def create_client(self, api_key: Optional[str] = None):
        """Create a Gemini chat model client.

        Returns:
            ChatGoogleGenerativeAI instance.
        """
        key = api_key or settings.GEMINI_API_KEY or "dummy-gemini-key"
        chat_client = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            include_thoughts=True,
            google_api_key=key,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        return chat_client


try:
    default_chat_client = GeminiChatClient().create_client()
except Exception:
    default_chat_client = None
