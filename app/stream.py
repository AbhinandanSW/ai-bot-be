from fastapi.responses import StreamingResponse
from app.models import ChatRequest, StreamChunk
from app.gemini import gemini_client
from app.db import get_conversation_history, save_message
from app.models import MessageRole
from typing import AsyncGenerator
import json
import logging

logger = logging.getLogger(__name__)


class StreamingService:
    """Handle Server-Sent Events streaming for chat responses"""

    @staticmethod
    async def stream_chat_response(
        request: ChatRequest, user_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream chat response using Server-Sent Events format"""

        try:
            # Get conversation history
            history = await get_conversation_history(request.thread_id)

            if not request.thread_id.startswith("req"):
                thread_id = f"req_{thread_id}"
            # Save user message
            await save_message(
                thread_id,
                request.session_id,
                MessageRole.USER,
                request.message,
                user_id,
            )

            # Stream response from Gemini
            full_response = ""
            async for chunk_data in gemini_client.stream_response(
                request.message, history, request.thread_id, request.session_id
            ):

                # Create stream chunk
                chunk = StreamChunk(**chunk_data)

                # Accumulate response for saving
                if chunk.type == "delta" and chunk.content:
                    full_response += chunk.content

                # Format as Server-Sent Event
                yield f"data: {chunk.model_dump_json()}\n\n"

                # Handle completion
                if chunk.type == "completion":
                    # Save assistant response
                    if full_response:
                        await save_message(
                            request.thread_id,
                            request.session_id,
                            MessageRole.ASSISTANT,
                            full_response,
                            user_id,
                        )
                    break

                # Handle errors
                elif chunk.type == "error":
                    logger.error(f"Streaming error: {chunk.error_message}")
                    break

        except Exception as e:
            logger.error(f"Error in streaming service: {e}")

            # Send error chunk
            error_chunk = StreamChunk(
                type="error",
                content="",
                thread_id=request.thread_id,
                session_id=request.session_id,
                has_artifact=False,
                error_message=str(e),
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"

    @staticmethod
    def create_streaming_response(
        request: ChatRequest, user_id: str
    ) -> StreamingResponse:
        """Create a FastAPI StreamingResponse for chat"""

        return StreamingResponse(
            StreamingService.stream_chat_response(request, user_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )
