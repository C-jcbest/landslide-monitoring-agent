"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication and chatbot functionality.
"""

from fastapi import APIRouter, Request

from app.api.v1.auth import router as auth_router
from app.api.v1.chatbot import router as chatbot_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])


@api_router.get("/health")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["api_health"][0])
async def health_check(request: Request):
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}
