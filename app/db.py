from supabase import create_client, Client
from app.config import settings
from app.models import ChatMessage, MessageRole, ConversationHistory
from typing import List, Optional
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

# Global Supabase client
supabase: Optional[Client] = None


async def init_database():
    """Initialize Supabase client"""
    global supabase

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be provided")

    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    logger.info("Supabase client initialized")


def get_supabase_client() -> Client:
    """Get the initialized Supabase client"""
    if supabase is None:
        raise RuntimeError("Supabase client not initialized")
    return supabase


async def save_message(
    thread_id: str, session_id: str, role: MessageRole, content: str, user_id: str
) -> bool:
    """Save a message to the database"""
    try:
        client = get_supabase_client()

        data = {
            "thread_id": thread_id,
            "session_id": session_id,
            "user_id": user_id,
            "role": role.value,
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
        }

        result = client.table("messages").insert(data).execute()

        # Update thread metadata
        await update_thread_metadata(thread_id, session_id, user_id)

        return True

    except Exception as e:
        logger.error(f"Error saving message: {e}")
        return False


async def update_thread_metadata(thread_id: str, session_id: str, user_id: str):
    """Update thread metadata (last activity, message count)"""
    try:
        client = get_supabase_client()

        # Get message count
        count_result = (
            client.table("messages")
            .select("*", count="exact")
            .eq("thread_id", thread_id)
            .execute()
        )

        message_count = count_result.count or 0

        # Upsert thread metadata
        thread_data = {
            "thread_id": thread_id,
            "user_id": user_id,
            "session_id": session_id,
            "message_count": message_count,
            "last_activity": datetime.utcnow().isoformat(),
        }

        client.table("threads").upsert(thread_data).execute()

    except Exception as e:
        logger.error(f"Error updating thread metadata: {e}")


async def get_conversation_history(
    thread_id: str, limit: int = 50
) -> List[ChatMessage]:
    """Get conversation history for a thread"""
    try:
        client = get_supabase_client()

        result = (
            client.table("messages")
            .select("*")
            .eq("thread_id", thread_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        thread_id_assistant = thread_id.replace("req_", "")
        assitant_result = (
            client.table("messages")
            .select("*")
            .eq("thread_id", thread_id_assistant)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )

        messages = []
        for row in result.data:
            messages.append(
                ChatMessage(
                    role=MessageRole(row["role"]),
                    content=row["content"],
                    timestamp=datetime.fromisoformat(
                        row["created_at"].replace("Z", "+00:00")
                    ),
                )
            )
        for row in assitant_result.data:
            messages.append(
                ChatMessage(
                    role=MessageRole(row["role"]),
                    content=row["content"],
                    timestamp=datetime.fromisoformat(
                        row["created_at"].replace("Z", "+00:00")
                    ),
                )
            )

        messages.sort(key=lambda msg: msg.timestamp)
        return messages

    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return []


async def get_session_threads(user_id: str) -> List[dict]:
    """Get all threads for a session"""
    try:
        client = get_supabase_client()
        result = (
            client.table("threads")
            .select("*")
            .eq("user_id", user_id)
            .order("last_activity", desc=True)
            .execute()
        )
        print(result.data)
        result_messages = (
            client.table("messages").select("*").eq("user_id", user_id).execute()
        )
        print("samp")

        updated_thread = []
        for thread in result.data:
            for message in result_messages.data:
                if thread["thread_id"] == message["thread_id"]:
                    # thread["message_count"] = message["message_count"]
                    # max content 50words in title
                    thread["title"] = " ".join(message["content"].split()[:10])
                    if message["role"] == "user":
                        updated_thread.append(thread)

                    break
        print(result_messages.data)
        return updated_thread

    except Exception as e:
        logger.error(f"Error getting session threads: {e}")
        return []


async def delete_thread(thread_id: str, session_id: str) -> bool:
    """Delete a thread and all its messages"""
    try:
        client = get_supabase_client()

        # Delete messages
        client.table("messages").delete().eq("thread_id", thread_id).execute()

        # Delete thread metadata
        client.table("threads").delete().eq("thread_id", thread_id).execute()

        return True

    except Exception as e:
        logger.error(f"Error deleting thread: {e}")
        return False


async def cleanup_old_conversations(days_old: int = 30):
    """Clean up conversations older than specified days"""
    try:
        client = get_supabase_client()

        cutoff_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=days_old)

        # Delete old messages
        client.table("messages").delete().lt(
            "created_at", cutoff_date.isoformat()
        ).execute()

        # Delete old threads
        client.table("threads").delete().lt(
            "last_activity", cutoff_date.isoformat()
        ).execute()

        logger.info(f"Cleaned up conversations older than {days_old} days")

    except Exception as e:
        logger.error(f"Error cleaning up conversations: {e}")
