from typing import Optional

from pydantic import BaseModel, Field


class CacheStatusResponse(BaseModel):
    """Response containing cache system diagnostics and status."""

    backend: str = Field(..., description="Active cache backend (redis or in_memory)")
    is_redis_available: bool = Field(..., description="Whether Redis is reachable")
    host: str = Field(..., description="Configured Redis host")
    port: int = Field(..., description="Configured Redis port")
    db: int = Field(..., description="Configured Redis DB number")
    default_ttl_seconds: int = Field(..., description="Default cache TTL in seconds")
    chat_ttl_seconds: int = Field(..., description="Conversation memory TTL in seconds")
    llm_cache_enabled: bool = Field(
        ..., description="Whether LangChain LLM cache is enabled"
    )
    keys_count: Optional[int] = Field(None, description="Number of cached keys")


class CacheClearRequest(BaseModel):
    """Request payload to clear cached items."""

    prefix: Optional[str] = Field(
        None,
        description="Optional key prefix to clear (e.g. 'search_cache:', 'report_cache:')",
    )


class CacheClearResponse(BaseModel):
    """Response returned upon clearing cache keys."""

    status: str = Field(
        default="success", description="Status of cache clear operation"
    )
    cleared_keys: int = Field(..., description="Number of keys cleared")
    prefix: Optional[str] = Field(None, description="Prefix that was cleared")
    backend: str = Field(..., description="Cache backend used")
