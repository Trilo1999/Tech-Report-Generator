from fastapi import APIRouter

from app.agents.supervisor_agent import supervisor
from app.schemas.core_schemas.chat_schema import (
    ChatClearResponse,
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from app.utils.core_utils.redis_utils import redis_history

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests using the supervisor agent.

    Args:
        request: ChatRequest with thread_id and query.

    Returns:
        ChatResponse with thread_id and agent answer.
    """
    answer = supervisor.invoke(thread_id=request.thread_id, query=request.query)
    return {"thread_id": request.thread_id, "answer": answer}


@router.get("/chat/history/{thread_id}", response_model=ChatHistoryResponse)
async def get_chat_history(thread_id: str):
    """Retrieve conversation message history for a given thread_id.

    Args:
        thread_id: Unique conversation identifier.

    Returns:
        ChatHistoryResponse with ordered message list and active storage backend.
    """
    raw_messages = redis_history.get_messages(thread_id)
    messages = [
        ChatMessage(role=m.get("role", "user"), content=m.get("content", ""))
        for m in raw_messages
    ]
    return {
        "thread_id": thread_id,
        "messages": messages,
        "backend": redis_history.get_backend(),
    }


@router.delete("/chat/history/{thread_id}", response_model=ChatClearResponse)
async def clear_chat_history(thread_id: str):
    """Clear conversation history for a given thread_id.

    Args:
        thread_id: Unique conversation identifier.

    Returns:
        ChatClearResponse indicating successful clearance.
    """
    redis_history.clear_history(thread_id)
    return {
        "thread_id": thread_id,
        "status": "cleared",
        "backend": redis_history.get_backend(),
    }
