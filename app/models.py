from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import EmailStr


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


class UserSignup(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(
        ..., min_length=1, max_length=100, description="User full name"
    )
    username: str = Field(..., min_length=3, max_length=30, description="Username")


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class AuthResponse(BaseModel):
    message: str
    user: Optional[Dict[str, Any]] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    requires_verification: bool = False


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    created_at: str
    email_verified: bool = False


class PasswordChange(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class PasswordReset(BaseModel):
    email: EmailStr = Field(..., description="Email address to reset password")


class EmailVerification(BaseModel):
    email: EmailStr = Field(..., description="Email address to verify")
    token: str = Field(..., description="Verification token")


# Update existing ChatRequest to include user context
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=50000)
    thread_id: str = Field(..., min_length=1, max_length=100)
    session_id: str = Field(..., min_length=1, max_length=100)


class AuthenticatedChatRequest(ChatRequest):
    """Chat request that includes user authentication context"""

    pass  # Inherits from ChatRequest, user info comes from dependency
