from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.db import init_database
from app.chat import router as chat_router
from app.auth import router as auth_router  # NEW
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    await init_database()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title="AI Coding Agent Backend",
    description="Claude-style AI coding assistant with authentication and streaming responses",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)  # NEW: Authentication routes
app.include_router(chat_router)  # Chat routes (now protected)


@app.get("/")
async def root():
    return {
        "message": "AI Coding Agent Backend",
        "status": "running",
        "features": ["authentication", "chat", "streaming"],
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-coding-agent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
