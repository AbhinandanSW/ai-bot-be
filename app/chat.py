from fastapi import APIRouter, Depends, HTTPException, Request
from app.models import ChatRequest, ConversationHistory
from app.stream import StreamingService
from app.db import get_conversation_history, get_session_threads, delete_thread
from app.rate_limiter import rate_limiter
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stream")
async def stream_chat(request: ChatRequest, http_request: Request):
    """Stream chat responses using Server-Sent Events"""

    # Rate limiting
    await rate_limiter.check_rate_limit(http_request)

    # Validate request
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Create streaming response
    return StreamingService.create_streaming_response(request)


@router.get("/history/{thread_id}")
async def get_chat_history(thread_id: str, limit: int = 50):
    """Get conversation history for a thread"""

    try:
        messages = await get_conversation_history(thread_id, limit)

        return {
            "thread_id": thread_id,
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
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history")


@router.get("/threads/{session_id}")
async def get_session_threads_endpoint(session_id: str):
    """Get all threads for a session"""

    try:
        threads = await get_session_threads(session_id)

        return {
            "session_id": session_id,
            "threads": threads,
            "thread_count": len(threads),
        }

    except Exception as e:
        logger.error(f"Error getting session threads: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve threads")


@router.delete("/threads/{thread_id}")
async def delete_thread_endpoint(
    thread_id: str, session_id: str, http_request: Request
):
    """Delete a thread and all its messages"""

    # Rate limiting
    await rate_limiter.check_rate_limit(http_request)

    try:
        success = await delete_thread(thread_id, session_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete thread")

        return {"message": f"Thread {thread_id} deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting thread: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete thread")


@router.get("/status")
async def get_chat_status():
    """Get chat service status"""
    return {
        "service": "chat",
        "status": "healthy",
        "features": {
            "streaming": True,
            "rate_limiting": True,
            "conversation_memory": True,
            "artifact_detection": True,
        },
    }
