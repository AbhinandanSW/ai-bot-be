import google.generativeai as genai
from app.config import settings
from app.models import ChatMessage, MessageRole
from typing import List, AsyncGenerator, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)


class GeminiClient:
    """Direct Gemini API client for text generation"""

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key is required")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction="""You are a helpful AI coding assistant. 
            Generate clean, well-documented code with explanations.
            When creating code, wrap it in markdown code blocks with proper language tags.
            Be concise but thorough in your explanations.
            If you generate code that could be used as an artifact, mention it clearly.""",
        )

    def _prepare_conversation_history(
        self, messages: List[ChatMessage]
    ) -> List[Dict[str, str]]:
        """Convert chat messages to Gemini format"""
        gemini_messages = []

        for message in messages:
            if message.role == MessageRole.USER:
                gemini_messages.append({"role": "user", "parts": [message.content]})
            elif message.role == MessageRole.ASSISTANT:
                gemini_messages.append({"role": "model", "parts": [message.content]})

        return gemini_messages

    def _detect_code_artifact(self, content: str) -> bool:
        """Detect if content contains code artifacts"""
        import re

        code_patterns = [
            r"``````",  # Code blocks
            r"function\s+\w+\s*\(",  # Function definitions
            r"class\s+\w+\s*[:\(]",  # Class definitions
            r"def\s+\w+\s*\(",  # Python functions
            r"const\s+\w+\s*=",  # JavaScript constants
            r"let\s+\w+\s*=",  # JavaScript variables
            r"var\s+\w+\s*=",  # JavaScript variables
            r"#include\s*<",  # C/C++ includes
            r"import\s+\w+",  # Import statements
            r"from\s+\w+\s+import",  # Python imports
        ]

        for pattern in code_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                return True

        return False

    async def stream_response(
        self,
        current_message: str,
        conversation_history: List[ChatMessage],
        thread_id: str,
        session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response from Gemini API"""

        try:
            # Prepare conversation history
            history = self._prepare_conversation_history(conversation_history)

            # Add current message
            history.append({"role": "user", "parts": [current_message]})

            # Start chat with history
            chat = self.model.start_chat(
                history=history[:-1]
            )  # Exclude current message

            # Generate streaming response
            full_response = ""
            response_stream = chat.send_message(
                current_message,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.TEMPERATURE,
                    max_output_tokens=settings.MAX_TOKENS,
                    top_p=0.95,
                    top_k=40,
                ),
            )

            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text

                    # Check for artifacts
                    has_artifact = self._detect_code_artifact(chunk.text)

                    yield {
                        "type": "delta",
                        "content": chunk.text,
                        "thread_id": thread_id,
                        "session_id": session_id,
                        "has_artifact": has_artifact,
                    }

            # Send completion signal
            final_has_artifact = self._detect_code_artifact(full_response)
            yield {
                "type": "completion",
                "content": "",
                "thread_id": thread_id,
                "session_id": session_id,
                "has_artifact": final_has_artifact,
            }

        except Exception as e:
            logger.error(f"Error in Gemini streaming: {e}")
            yield {
                "type": "error",
                "content": "",
                "thread_id": thread_id,
                "session_id": session_id,
                "has_artifact": False,
                "error_message": str(e),
            }


# Global client instance
gemini_client = GeminiClient()
