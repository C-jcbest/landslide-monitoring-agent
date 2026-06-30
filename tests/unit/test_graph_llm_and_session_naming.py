"""Unit tests for graph helpers, model fallback, and session naming."""

import asyncio
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from openai import OpenAIError

from app.core.langgraph.graph import LangGraphAgent
from app.services.llm.registry import LLMRegistry
from app.services.llm.service import LLMService
from app.services import session_naming
from app.utils.graph import extract_text_content, prepare_messages, process_llm_response
from app.schemas.chat import (
    Message,
    SessionTitle,
)

pytestmark = pytest.mark.unit


class FakeRunnable:
    """Small runnable fake for deterministic fallback and tool-binding tests."""

    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.bound_tools: list[Any] = []
        self.structured_calls: list[dict[str, Any]] = []
        self.invocations: list[Any] = []

    def bind_tools(self, tools: list[Any]) -> "FakeRunnable":
        self.bound_tools = tools
        return self

    def with_structured_output(self, schema: Any, **kwargs: Any) -> "FakeRunnable":
        self.structured_calls.append({"schema": schema, "kwargs": kwargs})
        return self

    async def ainvoke(self, _: Any) -> Any:
        self.invocations.append(_)
        if self.error:
            raise self.error
        return self.response


class FakeTool:
    """Async graph tool returning a fixed value after yielding control once."""

    def __init__(self, value: str) -> None:
        self.value = value
        self.calls: list[dict[str, Any]] = []

    async def ainvoke(self, arguments: dict[str, Any]) -> str:
        self.calls.append(arguments)
        await asyncio.sleep(0)
        return self.value


def test_extract_text_content_ignores_reasoning_blocks() -> None:
    """Only text blocks reach API clients; reasoning metadata remains internal."""
    content = [
        {"type": "reasoning", "id": "reasoning-1", "summary": "internal"},
        {"type": "text", "text": "visible"},
        " response",
    ]

    assert extract_text_content(content) == "visible response"


def test_process_llm_response_normalizes_structured_content() -> None:
    """Provider-specific content blocks normalize to plain assistant text."""
    response = AIMessage(content=[{"type": "text", "text": "answer"}])

    normalized = process_llm_response(response)

    assert normalized.content == "answer"


def test_prepare_messages_adds_system_prompt_and_keeps_latest_user_message() -> None:
    """The model always receives the system prompt before user content."""
    messages = [Message(role="user", content="Hello")]

    prepared = prepare_messages(messages, "System boundary")

    assert prepared[0] == Message(role="system", content="System boundary")
    assert prepared[-1].type == "human"
    assert prepared[-1].content == "Hello"


async def test_chat_internal_tool_runner_returns_all_tool_results() -> None:
    """Multiple requested read-only tools are executed inside the Chat node."""
    agent = LangGraphAgent()
    first_tool = FakeTool("first result")
    second_tool = FakeTool("second result")
    agent.tools_by_name = {"first": first_tool, "second": second_tool}

    messages = await agent._run_tool_calls(  # pyright: ignore[reportPrivateUsage]
        [
            {"name": "first", "args": {"query": "a"}, "id": "call-1"},
            {"name": "second", "args": {"query": "b"}, "id": "call-2"},
        ]
    )

    assert [message.content for message in messages] == ["first result", "second result"]
    assert first_tool.calls == [{"query": "a"}]
    assert second_tool.calls == [{"query": "b"}]


async def test_llm_fallback_tries_next_model_after_openai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A provider error advances the fallback loop and returns the next response."""
    service = LLMService()
    failing = FakeRunnable(error=OpenAIError("provider unavailable"))
    succeeding = FakeRunnable(response=AIMessage(content="recovered"))

    async def invoke(target: FakeRunnable, _: Any) -> Any:
        return await target.ainvoke([])

    monkeypatch.setattr(service, "_invoke_with_retry", invoke)
    monkeypatch.setattr(
        LLMRegistry,
        "LLMS",
        [{"name": "first", "llm": failing}, {"name": "second", "llm": succeeding}],
    )

    response = await service._fallback_loop(  # pyright: ignore[reportPrivateUsage]
        [],
        0,
        lambda index: [failing, succeeding][index],
        lambda index: index + 1,
    )

    assert response.content == "recovered"


def test_model_switch_rebinds_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback must preserve the graph's tool permissions on the new model."""
    first = FakeRunnable()
    second = FakeRunnable()
    monkeypatch.setattr(LLMRegistry, "LLMS", [{"name": "first", "llm": first}, {"name": "second", "llm": second}])
    service = LLMService()
    service._llm = first  # pyright: ignore[reportPrivateUsage]
    service._current_model_index = 0  # pyright: ignore[reportPrivateUsage]
    service.bind_tools(["safe-tool"])

    assert service._switch_to_next_model()  # pyright: ignore[reportPrivateUsage]
    assert service.get_llm() is second
    assert second.bound_tools == ["safe-tool"]


async def test_llm_call_enforces_total_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stuck provider call is bounded by the configured total timeout budget."""
    service = LLMService()

    async def never_returns(*_: Any) -> Any:
        await asyncio.sleep(1)

    monkeypatch.setattr(service, "_call_with_fallback", never_returns)
    monkeypatch.setattr("app.services.llm.service.settings.LLM_TOTAL_TIMEOUT", 0.01)

    with pytest.raises(RuntimeError, match="timed out"):
        await service.call([])


async def test_structured_llm_call_uses_json_mode_and_schema_instruction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Structured output uses JSON mode for OpenAI-compatible models that lack json_schema support."""
    runnable = FakeRunnable(response=SessionTitle(title="北斗站点数量"))
    monkeypatch.setattr(LLMRegistry, "LLMS", [{"name": "first", "llm": runnable}])
    service = LLMService()
    service._current_model_index = 0  # pyright: ignore[reportPrivateUsage]

    result = await service.call(
        [{"role": "user", "content": "现在北斗监测平台有多少监测点"}],
        response_format=SessionTitle,
    )

    assert result.title == "北斗站点数量"
    assert runnable.structured_calls[0]["kwargs"]["method"] == "json_mode"
    assert runnable.invocations[0][-1]["role"] == "system"
    assert "只输出一个 JSON object" in runnable.invocations[0][-1]["content"]
    assert "title" in runnable.invocations[0][-1]["content"]


@pytest.mark.parametrize(
    ("source", "expected"),
    [("  first   user message  ", "first user message"), ("   ", "新会话")],
)
def test_session_name_placeholder_is_stable(source: str, expected: str) -> None:
    """Placeholder titles are human-readable and bounded before persistence."""
    assert session_naming._build_placeholder(source) == expected  # pyright: ignore[reportPrivateUsage]


async def test_session_naming_claim_starts_one_background_task(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only a successful database claim schedules title generation."""
    persisted: list[tuple[str, str]] = []

    async def persist(session_id: str, message: str) -> None:
        persisted.append((session_id, message))

    monkeypatch.setattr(session_naming, "_claim_session", lambda *_: True)
    monkeypatch.setattr(session_naming, "_persist_session_name", persist)

    session_naming.maybe_name_session("session-1", "", [Message(role="user", content="Name this session")])
    await asyncio.sleep(0)

    assert persisted == [("session-1", "Name this session")]


def test_named_session_does_not_trigger_title_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A user-provided title is never overwritten by the automatic title task."""
    claimed = False

    def claim(*_: Any) -> bool:
        nonlocal claimed
        claimed = True
        return True

    monkeypatch.setattr(session_naming, "_claim_session", claim)

    session_naming.maybe_name_session("session-1", "Existing name", [Message(role="user", content="Ignore")])

    assert not claimed


async def test_persist_session_name_uses_structured_title(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful background title generation persists only the validated title value."""
    updates: list[tuple[str, str]] = []

    async def call(*_: Any, **__: Any):
        return session_naming.SessionTitle(title="Useful title")

    async def update(session_id: str, name: str) -> None:
        updates.append((session_id, name))

    monkeypatch.setattr(session_naming.llm_service, "call", call)
    monkeypatch.setattr(session_naming.database_service, "update_session_name", update)

    await session_naming._persist_session_name("session-1", "A long user message")  # pyright: ignore[reportPrivateUsage]

    assert updates == [("session-1", "Useful title")]
