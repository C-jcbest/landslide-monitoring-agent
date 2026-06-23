"""Database service tests using an isolated SQLModel schema."""

from collections.abc import Generator

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, create_engine

from app.models.user import User
from app.services.database import DatabaseService

pytestmark = pytest.mark.unit


@pytest.fixture
def database_service() -> Generator[DatabaseService, None, None]:
    """Construct a service without its production PostgreSQL initialization."""
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    service = object.__new__(DatabaseService)
    service.engine = engine

    yield service

    engine.dispose()


async def test_user_crud_and_unique_email_constraint(database_service: DatabaseService) -> None:
    """User reads and deletes operate on persisted records with unique email enforcement."""
    password = User.hash_password("ValidPass1!")
    created = await database_service.create_user("user@example.com", password, "User")

    assert created.id is not None
    assert (await database_service.get_user(created.id)).email == "user@example.com"  # pyright: ignore[reportOptionalMemberAccess]
    assert (await database_service.get_user_by_email("user@example.com")).id == created.id  # pyright: ignore[reportOptionalMemberAccess]

    with pytest.raises(IntegrityError):
        await database_service.create_user("user@example.com", password)

    assert await database_service.delete_user_by_email("user@example.com")
    assert not await database_service.delete_user_by_email("user@example.com")


async def test_session_crud_and_ordering(database_service: DatabaseService) -> None:
    """Sessions remain user-scoped, ordered, mutable, and deletable."""
    user = await database_service.create_user("owner@example.com", User.hash_password("ValidPass1!"))
    await database_service.create_session("first", user.id, name="First")
    await database_service.create_session("second", user.id, name="Second")

    sessions = await database_service.get_user_sessions(user.id)
    updated = await database_service.update_session_name("second", "Renamed")

    assert [session.id for session in sessions] == ["first", "second"]
    assert updated.name == "Renamed"
    assert await database_service.delete_session("first")
    assert not await database_service.delete_session("unknown")
    assert await database_service.get_session("first") is None


async def test_database_health_check_returns_true_for_working_engine(database_service: DatabaseService) -> None:
    """Health checks are a lightweight query against the configured engine."""
    assert await database_service.health_check()
