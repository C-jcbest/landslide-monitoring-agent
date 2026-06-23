"""Shared fixtures for deterministic, offline test execution."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# These values must be set before importing application modules.  They prevent
# startup-time tracing and keep all token tests deterministic and isolated.
os.environ["APP_ENV"] = "test"
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
os.environ["SESSION_NAMING_ENABLED"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-not-for-production"
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["NVIDIA_API_KEY"] = ""

from app.api.v1.auth import get_current_session, get_current_user
from app.main import app
from app.models.session import Session
from app.models.user import User


@pytest.fixture
def test_user() -> User:
    """Provide an authenticated user without touching the database."""
    return User(
        id=101,
        email="tester@example.com",
        username="Test User",
        hashed_password=User.hash_password("ValidPass1!"),
    )


@pytest.fixture
def test_session() -> Session:
    """Provide a session belonging to ``test_user``."""
    return Session(id="session-101", user_id=101, username="Test User")


@pytest_asyncio.fixture
async def client(test_user: User, test_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """Provide a FastAPI client with authentication dependencies replaced."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_current_session] = lambda: test_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    app.dependency_overrides.clear()
