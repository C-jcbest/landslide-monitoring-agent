"""API tests for authentication and session-management contracts."""

import pytest

from app.api.v1 import auth
from app.models.session import Session
from app.models.user import User
from app.utils.auth import create_access_token
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

pytestmark = pytest.mark.api


class FakeDatabase:
    """Async database double configurable per route test."""

    def __init__(self) -> None:
        self.user_by_email: User | None = None
        self.created_user: tuple[str, str, str | None] | None = None
        self.created_session: Session | None = None
        self.updated_name: tuple[str, str] | None = None
        self.sessions: list[Session] = []

    async def get_user_by_email(self, _: str) -> User | None:
        return self.user_by_email

    async def get_user(self, _: int) -> User | None:
        return None

    async def get_session(self, _: str) -> Session | None:
        return None

    async def create_user(self, email: str, password: str, username: str | None) -> User:
        self.created_user = (email, password, username)
        return User(id=202, email=email, username=username, hashed_password=password)

    async def create_session(self, session_id: str, user_id: int, username: str | None) -> Session:
        self.created_session = Session(id=session_id, user_id=user_id, username=username)
        return self.created_session

    async def update_session_name(self, session_id: str, name: str) -> Session:
        self.updated_name = (session_id, name)
        return Session(id=session_id, user_id=101, name=name, username="Test User")

    async def delete_session(self, _: str) -> bool:
        return True

    async def get_user_sessions(self, _: int) -> list[Session]:
        return self.sessions


async def test_register_normalizes_email_and_returns_token(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Registration creates a user with canonical email and a bearer token."""
    database = FakeDatabase()
    monkeypatch.setattr(auth, "db_service", database)

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "New.User@Example.COM", "password": "ValidPass1!", "username": "<Alice>"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "new.user@example.com"
    assert body["token"]["token_type"] == "bearer"
    assert database.created_user is not None
    assert database.created_user[0] == "new.user@example.com"
    assert database.created_user[2] == "&lt;Alice&gt;"


async def test_register_rejects_duplicate_email(client, monkeypatch: pytest.MonkeyPatch, test_user: User) -> None:
    """Duplicate account creation returns a stable client error without a write."""
    database = FakeDatabase()
    database.user_by_email = test_user
    monkeypatch.setattr(auth, "db_service", database)

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "tester@example.com", "password": "ValidPass1!"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"
    assert database.created_user is None


async def test_register_returns_formatted_validation_errors(client) -> None:
    """Invalid request bodies use the application-wide 422 response contract."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "invalid", "password": "weak"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Validation error"
    assert body["errors"]


async def test_login_rejects_unsupported_grant_type(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """The login endpoint only supports the documented password grant."""
    monkeypatch.setattr(auth, "db_service", FakeDatabase())

    response = await client.post(
        "/api/v1/auth/login",
        data={"email": "tester@example.com", "password": "ValidPass1!", "grant_type": "refresh_token"},
    )

    assert response.status_code == 400
    assert "Unsupported grant type" in response.json()["detail"]


async def test_login_returns_token_for_valid_credentials(
    client, monkeypatch: pytest.MonkeyPatch, test_user: User
) -> None:
    """Correct form credentials issue a bearer access token."""
    database = FakeDatabase()
    database.user_by_email = test_user
    monkeypatch.setattr(auth, "db_service", database)

    response = await client.post(
        "/api/v1/auth/login",
        data={"email": "tester@example.com", "password": "ValidPass1!"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


async def test_create_session_uses_authenticated_user(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """A session is owned by the authenticated user supplied by the dependency."""
    database = FakeDatabase()
    monkeypatch.setattr(auth, "db_service", database)

    response = await client.post("/api/v1/auth/session")

    assert response.status_code == 200
    assert database.created_session is not None
    assert database.created_session.user_id == 101
    assert response.json()["session_id"] == database.created_session.id


async def test_update_session_name_rejects_other_session(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """A session token cannot modify a different session identifier."""
    monkeypatch.setattr(auth, "db_service", FakeDatabase())

    response = await client.patch("/api/v1/auth/session/another-session/name", data={"name": "Other"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot modify other sessions"


async def test_list_sessions_returns_only_authenticated_users_sessions(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Session listing delegates using the current user's identifier."""
    database = FakeDatabase()
    database.sessions = [
        Session(id="first", user_id=101, name="First"),
        Session(id="second", user_id=101, name="Second"),
    ]
    monkeypatch.setattr(auth, "db_service", database)

    response = await client.get("/api/v1/auth/sessions")

    assert response.status_code == 200
    assert [item["session_id"] for item in response.json()] == ["first", "second"]


async def test_delete_session_allows_matching_session_token(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """The current session can delete itself and receives a successful empty response."""
    monkeypatch.setattr(auth, "db_service", FakeDatabase())

    response = await client.delete("/api/v1/auth/session/session-101")

    assert response.status_code == 200
    assert response.content == b"null"


async def test_current_user_rejects_unknown_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid JWTs for deleted users do not authenticate a request."""
    database = FakeDatabase()
    monkeypatch.setattr(auth, "db_service", database)
    token = create_access_token("999").access_token
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as error:
        await auth.get_current_user(credentials)

    assert error.value.status_code == 404


async def test_current_session_rejects_invalid_jwt() -> None:
    """Malformed session tokens are rejected before any database access."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt")

    with pytest.raises(HTTPException) as error:
        await auth.get_current_session(credentials)

    assert error.value.status_code == 422
