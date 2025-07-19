from fastapi import APIRouter, Depends, HTTPException, Request
from app.models import AuthenticatedChatRequest, ConversationHistory
from app.stream import StreamingService
from app.db import get_conversation_history, get_session_threads, delete_thread
from app.auth_dependencies import get_current_user, get_current_user_with_rate_limit
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def stream_chat(
    request: AuthenticatedChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_with_rate_limit),
    http_request: Request = None,
):
    """Stream chat responses using Server-Sent Events - PROTECTED ROUTE"""

    # Validate request
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Add user context to the request
    user_id = current_user.get("id")

    # Ensure user owns the session
    # if not request.session_id.startswith(user_id):
    #     request.session_id = f"{user_id}_{request.session_id}"

    # # Ensure user owns the thread
    # if not request.thread_id.startswith(user_id):
    #     request.thread_id = f"{user_id}_{request.thread_id}"

    logger.info(f"User {user_id} starting chat in thread {request.thread_id}")

    # Create streaming response
    return StreamingService.create_streaming_response(request, user_id)


@router.get("/history/{thread_id}")
async def get_chat_history(
    thread_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = 50,
):
    """Get conversation history for a thread - PROTECTED ROUTE"""

    user_id = current_user.get("id")

    # Ensure user owns the thread
    if not thread_id.startswith(user_id):
        thread_id = f"{user_id}_{thread_id}"

    try:
        messages = await get_conversation_history(thread_id, limit)

        return {
            "thread_id": thread_id,
            "user_id": user_id,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                }
                for msg in messages
            ],
            "message_count": len(messages),
        }

    except Exception as e:
        logger.error(f"Error getting chat history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history")


@router.get("/threads")
async def get_user_threads(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get all threads for the current user - PROTECTED ROUTE"""

    user_id = current_user.get("id")
    session_id_prefix = f"{user_id}_"

    try:
        # Get threads that belong to this user
        all_threads = await get_session_threads(session_id_prefix)

        # Filter threads that belong to the user
        user_threads = [
            thread
            for thread in all_threads
            if thread.get("session_id", "").startswith(session_id_prefix)
        ]

        return {
            "user_id": user_id,
            "threads": user_threads,
            "thread_count": len(user_threads),
        }

    except Exception as e:
        logger.error(f"Error getting threads for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve threads")


@router.delete("/threads/{thread_id}")
async def delete_thread_endpoint(
    thread_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_with_rate_limit),
):
    """Delete a thread and all its messages - PROTECTED ROUTE"""

    user_id = current_user.get("id")
    session_id = f"{user_id}_default"  # or derive from thread

    # Ensure user owns the thread
    if not thread_id.startswith(user_id):
        thread_id = f"{user_id}_{thread_id}"

    try:
        success = await delete_thread(thread_id, session_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete thread")

        return {"message": f"Thread {thread_id} deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting thread {thread_id} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete thread")


@router.get("/status")
async def get_chat_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get chat service status for authenticated user"""

    return {
        "service": "chat",
        "status": "healthy",
        "user_id": current_user.get("id"),
        "user_email": current_user.get("email"),
        "features": {
            "streaming": True,
            "rate_limiting": True,
            "conversation_memory": True,
            "artifact_detection": True,
            "user_isolation": True,
        },
    }
