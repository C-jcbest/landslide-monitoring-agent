"""Integration tests requiring the isolated Docker PostgreSQL and Valkey stack."""

import os
import uuid

import pytest
from sqlalchemy import inspect

from app.core.cache import ValkeyCacheService
from app.models.user import User
from app.services.database import DatabaseService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1",
        reason="requires docker-compose.test.yml; run make test-integration",
    ),
]


async def test_postgres_migration_and_database_service_crud() -> None:
    """Migrated PostgreSQL accepts the user and session lifecycle used by the API."""
    service = DatabaseService()
    email = f"integration-{uuid.uuid4()}@example.com"
    user = await service.create_user(email, User.hash_password("ValidPass1!"), "Integration")
    session_id = str(uuid.uuid4())

    try:
        tables = set(inspect(service.engine).get_table_names())
        session = await service.create_session(session_id, user.id, username=user.username)

        assert {"user", "session", "thread"}.issubset(tables)
        assert await service.health_check()
        assert session.user_id == user.id
        assert (await service.get_session(session_id)).id == session_id  # pyright: ignore[reportOptionalMemberAccess]
    finally:
        await service.delete_session(session_id)
        await service.delete_user_by_email(email)
        service.engine.dispose()


async def test_valkey_cache_round_trip() -> None:
    """The distributed cache supports set, get, delete, and close semantics."""
    cache = ValkeyCacheService(default_ttl=30)
    key = f"integration:{uuid.uuid4()}"

    await cache.initialize()
    try:
        await cache.set(key, "cached")
        assert await cache.get(key) == "cached"
        await cache.delete(key)
        assert await cache.get(key) is None
    finally:
        await cache.close()
