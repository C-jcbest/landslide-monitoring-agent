"""Stateful LangGraph agent tests with fully local graph and memory doubles."""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message

pytestmark = pytest.mark.unit


class FakeMemoryService:
    """Memory replacement that records query and asynchronous persistence calls."""

    def __init__(self) -> None:
        self.search_calls: list[tuple[str | None, str]] = []
        self.add_calls: list[tuple[str | None, list[dict[str, Any]], dict[str, Any] | None]] = []

    async def search(self, user_id: str | None, query: str) -> str:
        self.search_calls.append((user_id, query))
        return "* remembered preference"

    async def add(self, user_id: str | None, messages: list[dict[str, Any]], metadata: dict[str, Any] | None) -> None:
        self.add_calls.append((user_id, messages, metadata))


class FakeGraph:
    """Graph fake supporting the state and streaming calls used by the agent."""

    def __init__(self) -> None:
        self.inputs: list[Any] = []
        self.state = SimpleNamespace(next=(), tasks=[], values={"messages": []})
        self.response = {"messages": [HumanMessage(content="Question"), AIMessage(content="Answer")]}

    async def aget_state(self, config: dict[str, Any]) -> SimpleNamespace:
        return self.state

    async def ainvoke(
        self,
        graph_input: Any | None = None,
        config: dict[str, Any] | None = None,
        *,
        input: Any | None = None,
    ) -> dict[str, list[Any]]:
        graph_input = input if input is not None else graph_input
        self.inputs.append(graph_input)
        self.state = SimpleNamespace(next=(), tasks=[], values=self.response)
        return self.response

    async def astream(self, graph_input: Any, config: dict[str, Any], stream_mode: str):
        self.inputs.append(graph_input)
        yield AIMessageChunk(content="Part one "), {}
        yield AIMessageChunk(content="part two"), {}
        self.state = SimpleNamespace(next=(), tasks=[], values=self.response)


async def test_get_response_uses_memory_and_persists_completed_conversation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Normal graph invocation searches memory and schedules user-scoped persistence."""
    agent = LangGraphAgent()
    graph = FakeGraph()
    memory = FakeMemoryService()

    async def get_graph() -> FakeGraph:
        return graph

    monkeypatch.setattr(agent, "_get_graph", get_graph)
    monkeypatch.setattr("app.core.langgraph.graph.memory_service", memory)

    messages = [Message(role="user", content="Question")]
    response = await agent.get_response(messages, "session-1", user_id="user-1", username="Alice")
    await asyncio.sleep(0)

    assert [message.content for message in response] == ["Question", "Answer"]
    assert memory.search_calls == [("user-1", "Question")]
    assert graph.inputs[0]["long_term_memory"] == "* remembered preference"
    assert memory.add_calls[0][0] == "user-1"
    assert memory.add_calls[0][2]["session_id"] == "session-1"


async def test_stream_response_yields_text_and_updates_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Streaming ignores non-text internals and stores completed conversation state."""
    agent = LangGraphAgent()
    graph = FakeGraph()
    memory = FakeMemoryService()

    async def get_graph() -> FakeGraph:
        return graph

    monkeypatch.setattr(agent, "_get_graph", get_graph)
    monkeypatch.setattr("app.core.langgraph.graph.memory_service", memory)

    chunks = [chunk async for chunk in agent.get_stream_response([Message(role="user", content="Question")], "session-1", "user-1")]
    await asyncio.sleep(0)

    assert chunks == ["Part one ", "part two"]
    assert memory.search_calls == [("user-1", "Question")]
    assert memory.add_calls[0][0] == "user-1"


async def test_get_chat_history_returns_empty_when_checkpoint_has_no_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """New sessions do not fail when no graph checkpoint has been saved yet."""
    agent = LangGraphAgent()
    graph = FakeGraph()
    graph.state = SimpleNamespace(next=(), tasks=[], values={})

    async def get_graph() -> FakeGraph:
        return graph

    monkeypatch.setattr(agent, "_get_graph", get_graph)

    assert await agent.get_chat_history("new-session") == []
