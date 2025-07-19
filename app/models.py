from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=50000)
    thread_id: str = Field(..., min_length=1, max_length=100)
    session_id: str = Field(..., min_length=1, max_length=100)


class StreamChunk(BaseModel):
    type: Literal["delta", "completion", "error", "artifact"]
    content: Optional[str] = None
    thread_id: str
    session_id: str
    has_artifact: bool = False
    error_message: Optional[str] = None


class ConversationHistory(BaseModel):
    thread_id: str
    session_id: str
    messages: List[ChatMessage]
    message_count: int
    created_at: datetime
    updated_at: datetime


class ThreadSummary(BaseModel):
    thread_id: str
    title: str
    message_count: int
    last_message_at: datetime
