from typing import List

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    thread_id: str = Field(..., description="Conversation thread id")
    query: str = Field(..., description="User query")


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""

    thread_id: str = Field(..., description="Conversation thread id")
    answer: str = Field(..., description="Assistant response")


class ChatMessage(BaseModel):
    """Single conversation message representation."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message text content")


class ChatHistoryResponse(BaseModel):
    """Response containing conversation message history."""

    thread_id: str = Field(..., description="Conversation thread id")
    messages: List[ChatMessage] = Field(
        default_factory=list, description="Ordered conversation messages"
    )
    backend: str = Field(..., description="Active storage backend (redis or in_memory)")


class ChatClearResponse(BaseModel):
    """Response returned upon clearing conversation memory."""

    thread_id: str = Field(..., description="Conversation thread id")
    status: str = Field(default="cleared", description="Status message")
    backend: str = Field(..., description="Active storage backend")
