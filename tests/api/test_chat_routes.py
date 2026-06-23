"""API tests for chat, streaming, and stored conversation behavior."""

from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest

from app.api.v1 import chatbot
from app.main import database_service
from app.schemas.chat import Message

pytestmark = pytest.mark.api


class FakeGraph:
    """Minimal graph state reader for route tests that do not need PostgreSQL."""

    async def aget_state(self, _) -> SimpleNamespace:
        return SimpleNamespace(next=(), tasks=[])


async def _get_fake_graph() -> FakeGraph:
    """Return an idle graph state for API route tests."""
    return FakeGraph()


async def test_chat_returns_agent_messages_and_request_id(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """The JSON chat endpoint preserves the response schema without a real model."""
    received: dict[str, object] = {}

    async def get_response(messages, session_id: str, user_id: str, username: str):
        received.update({"messages": messages, "session_id": session_id, "user_id": user_id, "username": username})
        return [Message(role="assistant", content="Offline answer")]

    monkeypatch.setattr(chatbot.agent, "get_response", get_response)
    monkeypatch.setattr(chatbot.agent, "_get_graph", _get_fake_graph)

    response = await client.post("/api/v1/chatbot/chat", json={"messages": [{"role": "user", "content": "Hello"}]})

    assert response.status_code == 200
    assert response.json()["messages"] == [{"role": "assistant", "content": "Offline answer"}]
    assert response.json()["request_id"]
    assert received["session_id"] == "session-101"
    assert received["user_id"] == "101"


async def test_chat_rejects_script_before_calling_agent(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Input validation blocks unsafe content before it reaches an LLM tool chain."""
    called = False

    async def get_response(*_):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(chatbot.agent, "get_response", get_response)

    response = await client.post(
        "/api/v1/chatbot/chat",
        json={"messages": [{"role": "user", "content": "<script>steal()</script>"}]},
    )

    assert response.status_code == 422
    assert not called


async def test_chat_failure_keeps_http_error_contract(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Agent errors do not expose provider details to API clients."""
    async def get_response(*_, **__):
        raise RuntimeError("provider secret: sk-test-should-not-leak")

    monkeypatch.setattr(chatbot.agent, "get_response", get_response)
    monkeypatch.setattr(chatbot.agent, "_get_graph", _get_fake_graph)

    response = await client.post("/api/v1/chatbot/chat", json={"messages": [{"role": "user", "content": "Hello"}]})

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to process chat request"
    assert "sk-test" not in response.text


async def test_stream_returns_chunks_and_completion_event(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """The streaming route emits ordered SSE data followed by ``done=true``."""
    async def get_stream_response(*_, **__) -> AsyncGenerator[str, None]:
        yield "first "
        yield "second"

    monkeypatch.setattr(chatbot.agent, "get_stream_response", get_stream_response)

    response = await client.post(
        "/api/v1/chatbot/chat/stream",
        json={"messages": [{"role": "user", "content": "Stream please"}]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'data: {"request_id"' in response.text
    assert '"content": "first "' in response.text
    assert '"content": "second"' in response.text
    assert '"done": true' in response.text


async def test_stream_failure_does_not_expose_provider_error(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """SSE errors use a safe generic message rather than external-service details."""
    async def get_stream_response(*_, **__) -> AsyncGenerator[str, None]:
        raise RuntimeError("provider secret: sk-test-should-not-leak")
        yield "unreachable"

    monkeypatch.setattr(chatbot.agent, "get_stream_response", get_stream_response)

    response = await client.post(
        "/api/v1/chatbot/chat/stream",
        json={"messages": [{"role": "user", "content": "Stream please"}]},
    )

    assert response.status_code == 200
    assert "Unable to process chat stream" in response.text
    assert "sk-test" not in response.text


async def test_get_and_clear_chat_history(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """History retrieval and clearing operate only on the authenticated session."""
    cleared: list[str] = []

    async def get_chat_history(session_id: str) -> list[Message]:
        assert session_id == "session-101"
        return [Message(role="user", content="Saved"), Message(role="assistant", content="Answer")]

    async def clear_chat_history(session_id: str) -> None:
        cleared.append(session_id)

    monkeypatch.setattr(chatbot.agent, "get_chat_history", get_chat_history)
    monkeypatch.setattr(chatbot.agent, "clear_chat_history", clear_chat_history)
    monkeypatch.setattr(chatbot.agent, "_get_graph", _get_fake_graph)

    history = await client.get("/api/v1/chatbot/messages")
    cleared_response = await client.delete("/api/v1/chatbot/messages")

    assert history.status_code == 200
    assert [message["content"] for message in history.json()["messages"]] == ["Saved", "Answer"]
    assert cleared_response.status_code == 200
    assert cleared == ["session-101"]


async def test_health_endpoints_report_api_and_database_state(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Liveness and readiness endpoints expose their documented response contracts."""
    async def unhealthy() -> bool:
        return False

    monkeypatch.setattr(database_service, "health_check", unhealthy)

    api_health = await client.get("/api/v1/health")
    readiness = await client.get("/health")

    assert api_health.status_code == 200
    assert api_health.json()["status"] == "healthy"
    assert readiness.status_code == 503
    assert readiness.json()["status"] == "degraded"
    assert readiness.json()["components"]["database"] == "unhealthy"


async def test_root_reports_service_metadata(client) -> None:
    """The unauthenticated root endpoint exposes the documented discovery fields."""
    response = await client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["swagger_url"] == "/docs"
