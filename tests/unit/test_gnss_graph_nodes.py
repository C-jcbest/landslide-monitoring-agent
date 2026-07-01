"""Unit tests for the GNSS-only LangGraph workflow."""

from typing import Any

import pytest
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from app.core.langgraph import graph as graph_module
from app.core.langgraph.graph import LangGraphAgent
from app.core.langgraph.tools import open_meteo_weather as weather_module
from app.schemas.beidou_station import (
    AgentPlan,
    BeidouSession,
    BeidouStation,
    BeidouStationGroup,
    StationCandidate,
)
from app.schemas.graph import GraphState

pytestmark = pytest.mark.unit

SESSION_UUID = "00000000-0000-4000-8000-000000000000"
STATION_UUID = "22222222-2222-4222-8222-222222222222"
OTHER_STATION_UUID = "99999999-9999-4999-8999-999999999999"


def _station(uuid: str = STATION_UUID, name: str = "北坡 GNSS 01") -> BeidouStation:
    return BeidouStation(
        station_group_uuid="11111111-1111-4111-8111-111111111111",
        station_group_name="北坡监测组",
        station_uuid=uuid,
        device_uuid="DEV-BP-001",
        station_name=name,
        station_type=3,
        station_location="北坡一号滑坡体",
        station_status=10,
        latitude="39.759630522",
        longitude="116.986252277",
    )


def _candidate(uuid: str = STATION_UUID, name: str = "北坡 GNSS 01") -> StationCandidate:
    return StationCandidate(
        station_uuid=uuid,
        station_name=name,
        station_group_name="北坡监测组",
        device_uuid="DEV-BP-001",
        station_type=3,
        station_status=10,
        station_location="北坡一号滑坡体",
    )


def _config(user_id: str | None = "101") -> dict[str, Any]:
    metadata = {"session_id": "session-101", "username": "tester"}
    if user_id is not None:
        metadata["user_id"] = user_id
    return {"configurable": {"thread_id": "session-101"}, "metadata": metadata}


class FakeLLMService:
    """LLM fake returning queued structured outputs and AI messages."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []
        self.bound_tools: list[Any] = []

    async def call(self, messages: Any, **kwargs: Any) -> Any:
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return self.responses.pop(0)

    def get_llm(self) -> Any:
        return None

    def bind_tools(self, tools: list[Any]) -> "FakeLLMService":
        self.bound_tools = tools
        return self


class FakeSessionProvider:
    """User-scoped Beidou session provider fake."""

    def __init__(self, session: BeidouSession | None) -> None:
        self.session = session
        self.calls: list[str] = []

    async def get_session(self, user_id: str) -> BeidouSession | None:
        self.calls.append(user_id)
        return self.session


class FakeStationService:
    """Station service fake with deterministic candidates and details."""

    def __init__(self, candidates: list[StationCandidate]) -> None:
        self.candidates = candidates
        self.groups = [
            BeidouStationGroup(
                station_group_uuid="11111111-1111-4111-8111-111111111111",
                station_group_name="北坡监测组",
                station_count=2,
            )
        ]
        self.group_calls = 0
        self.candidate_calls = 0
        self.detail_calls: list[str] = []

    async def get_station_groups(self, session: BeidouSession) -> list[BeidouStationGroup]:
        assert session.session_uuid == SESSION_UUID
        self.group_calls += 1
        return self.groups

    async def get_station_candidates(self, session: BeidouSession) -> list[StationCandidate]:
        assert session.session_uuid == SESSION_UUID
        self.candidate_calls += 1
        return self.candidates

    async def get_station_detail(self, session: BeidouSession, station_uuid: str) -> BeidouStation:
        assert session.session_uuid == SESSION_UUID
        self.detail_calls.append(station_uuid)
        return _station(station_uuid)


class FakeWeatherService:
    """Weather service fake for read-only environmental facts."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def query_for_station(self, station: BeidouStation) -> dict[str, Any]:
        self.calls.append(station.station_uuid)
        return {"ok": True, "rain_summary": {"recent_24h_precipitation": 18.6}}


async def test_request_planner_routes_gnss_request_to_gnss_agent() -> None:
    """GNSS requests enter the GNSS authorization preflight branch."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService(
        [AgentPlan(route="gnss", intent="station_list", needs_station=False, reason="北斗站点数量查询。")]
    )
    state = GraphState(messages=[HumanMessage(content="现在北斗监测平台有多少监测点")])

    command = await agent._request_planner(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "gnss_preflight"
    assert command.update["route"] == "gnss"
    assert command.update["gnss_tool_rounds"] == 0


async def test_request_planner_receives_recent_dialogue_context() -> None:
    """Planner sees recent user and assistant messages when resolving follow-up intent."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService(
        [AgentPlan(route="gnss", intent="station_list", needs_station=False, reason="延续上一轮站点数量查询。")]
    )
    state = GraphState(
        messages=[
            HumanMessage(content="现在北斗监测平台有多少监测点"),
            AIMessage(content="当前北斗监测平台共有 20 个监测点。"),
            HumanMessage(content="重新查询"),
        ]
    )

    await agent._request_planner(state, _config())  # pyright: ignore[reportPrivateUsage]

    planner_messages = agent.llm_service.calls[0]["messages"]
    planner_context = planner_messages[1]["content"]
    assert "用户：现在北斗监测平台有多少监测点" in planner_context
    assert "助手：当前北斗监测平台共有 20 个监测点。" in planner_context
    assert "用户：重新查询" in planner_context
    assert "请判断最后一条用户消息的真实业务意图" in planner_context


async def test_request_planner_context_excludes_tool_messages() -> None:
    """Planner context excludes tool JSON to reduce prompt-injection and payload noise."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService(
        [AgentPlan(route="gnss", intent="station_list", needs_station=False, reason="站点数量查询。")]
    )
    state = GraphState(
        messages=[
            HumanMessage(content="现在北斗监测平台有多少监测点"),
            ToolMessage(
                content='{"ok": true, "station_candidates": [{"station_name": "北坡 GNSS 01"}]}', tool_call_id="call-1"
            ),
            AIMessage(content="当前北斗监测平台共有 20 个监测点。"),
            HumanMessage(content="重新查询"),
        ]
    )

    await agent._request_planner(state, _config())  # pyright: ignore[reportPrivateUsage]

    planner_messages = agent.llm_service.calls[0]["messages"]
    planner_context = planner_messages[1]["content"]
    assert "station_candidates" not in planner_context
    assert "北坡 GNSS 01" not in planner_context
    assert "用户：重新查询" in planner_context


async def test_request_planner_routes_weather_request_to_chat() -> None:
    """Non-GNSS weather requests enter ordinary chat without Beidou authorization."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService(
        [AgentPlan(route="chat", intent="weather", reason="普通天气查询不属于 GNSS 授权业务。")]
    )
    state = GraphState(messages=[HumanMessage(content="今天有雨吗？")])

    command = await agent._request_planner(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "chat"
    assert command.update["route"] == "chat"
    assert command.update["unsupported_reason"] == ""


async def test_gnss_preflight_auth_missing_routes_to_render_without_agent() -> None:
    """GNSS requests without Beidou credentials stop before the GNSS agent."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService([])
    agent.beidou_session_provider = FakeSessionProvider(None)
    state = GraphState(
        messages=[HumanMessage(content="列出我的北斗站点")],
        route="gnss",
        plan=AgentPlan(route="gnss", intent="station_list"),
    )

    command = await agent._gnss_preflight(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "render"
    assert command.update["gate"].status == "auth_missing"
    assert command.update["gate"].reason_code == "beidou_credential_missing"
    assert agent.llm_service.calls == []


async def test_chat_tools_weather_does_not_require_beidou_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ordinary weather calls execute in chat_tools without resolving a Beidou session."""
    agent = LangGraphAgent()
    agent.beidou_session_provider = FakeSessionProvider(None)
    weather_calls: list[dict[str, Any]] = []

    async def fake_weather(**kwargs: Any) -> str:
        weather_calls.append(kwargs)
        return '{"ok":true,"rain_summary":{"recent_24h_precipitation":2.4}}'

    monkeypatch.setattr(weather_module, "query_open_meteo_weather", fake_weather)
    state = GraphState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_open_meteo_weather",
                        "args": {"latitude": 30.294, "longitude": 120.1619},
                        "id": "call-weather",
                    }
                ],
            )
        ],
        route="chat",
    )

    command = await agent._chat_tools(state, _config(user_id=None))  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "chat"
    assert weather_calls == [{"latitude": 30.294, "longitude": 120.1619, "start_date": None, "end_date": None, "forecast_days": 7}]
    assert agent.beidou_session_provider.calls == []
    assert command.update["messages"][0].name == "query_open_meteo_weather"


async def test_gnss_agent_routes_tool_calls_to_gnss_tools() -> None:
    """GNSS agent sends read-only tool calls to the GNSS tools node."""
    tool_call = {
        "name": "get_beidou_station_candidates",
        "args": {},
        "id": "call-1",
    }
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService([AIMessage(content="", tool_calls=[tool_call])])
    state = GraphState(
        messages=[HumanMessage(content="列出我的北斗站点")],
        route="gnss",
        plan=AgentPlan(route="gnss", intent="station_list", needs_station=False),
    )

    command = await agent._gnss_agent(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "gnss_tools"
    assert command.update["gnss_tool_rounds"] == 1
    assert command.update["messages"][0].tool_calls[0]["name"] == "get_beidou_station_candidates"


async def test_gnss_tools_execute_with_user_scoped_session() -> None:
    """GNSS tools read facts through the current user's Beidou session without exposing SessionUUID input."""
    agent = LangGraphAgent()
    station_service = FakeStationService([_candidate(), _candidate(OTHER_STATION_UUID, "北坡 GNSS 02")])
    agent.beidou_session_provider = FakeSessionProvider(BeidouSession(session_uuid=SESSION_UUID))
    agent.beidou_station_service = station_service
    state = GraphState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_beidou_station_candidates",
                        "args": {},
                        "id": "call-1",
                    }
                ],
            )
        ],
        route="gnss",
    )

    command = await agent._gnss_tools(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "gnss_agent"
    assert station_service.candidate_calls == 1
    message = command.update["messages"][0]
    assert isinstance(message, ToolMessage)
    assert "北坡 GNSS 01" in str(message.content)
    assert "移动站 RTK 模式" in str(message.content)
    assert "正常（监测点状态=10）" in str(message.content)
    assert SESSION_UUID not in str(message.content)


async def test_gnss_station_weather_requires_detail_then_coordinate_weather(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Station weather is composed from station detail and coordinate weather calls."""
    agent = LangGraphAgent()
    station_service = FakeStationService([_candidate()])
    agent.beidou_session_provider = FakeSessionProvider(BeidouSession(session_uuid=SESSION_UUID))
    agent.beidou_station_service = station_service
    weather_calls: list[dict[str, Any]] = []

    async def fake_weather(**kwargs: Any) -> str:
        weather_calls.append(kwargs)
        return '{"ok":true,"rain_summary":{"recent_24h_precipitation":18.6}}'

    monkeypatch.setattr(graph_module, "query_open_meteo_weather", fake_weather)

    detail_state = GraphState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_beidou_station_detail",
                        "args": {"station_uuid": STATION_UUID},
                        "id": "call-detail",
                    }
                ],
            )
        ],
        route="gnss",
    )
    detail_command = await agent._gnss_tools(detail_state, _config())  # pyright: ignore[reportPrivateUsage]
    detail_payload = detail_command.update["messages"][0].content

    assert station_service.detail_calls == [STATION_UUID]
    assert "latitude" in str(detail_payload)
    assert weather_calls == []

    weather_state = GraphState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_open_meteo_weather",
                        "args": {"latitude": 39.759630522, "longitude": 116.986252277},
                        "id": "call-weather",
                    }
                ],
            )
        ],
        route="gnss",
    )
    weather_command = await agent._gnss_tools(weather_state, _config())  # pyright: ignore[reportPrivateUsage]

    assert weather_command.goto == "gnss_agent"
    assert weather_calls == [
        {
            "latitude": 39.759630522,
            "longitude": 116.986252277,
            "start_date": None,
            "end_date": None,
            "forecast_days": 7,
        }
    ]
    assert "rain_summary" in str(weather_command.update["messages"][0].content)


async def test_removed_station_weather_wrapper_is_not_authorized() -> None:
    """The old mixed station-weather tool is no longer accepted by GNSS tools."""
    agent = LangGraphAgent()
    agent.beidou_session_provider = FakeSessionProvider(BeidouSession(session_uuid=SESSION_UUID))
    state = GraphState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_beidou_station_weather",
                        "args": {"station_uuid": STATION_UUID},
                        "id": "call-weather",
                    }
                ],
            )
        ],
        route="gnss",
    )

    command = await agent._gnss_tools(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "gnss_agent"
    assert "unknown_gnss_tool" in str(command.update["messages"][0].content)


async def test_gnss_agent_routes_final_reply_to_action_router() -> None:
    """When fact collection is done, GNSS agent stores the reply and enters action routing."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService([AIMessage(content="当前账号可访问 2 个北斗监测点。")])
    state = GraphState(
        messages=[HumanMessage(content="现在北斗监测平台有多少监测点")],
        route="gnss",
        plan=AgentPlan(route="gnss", intent="station_list", needs_station=False),
    )

    command = await agent._gnss_agent(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "action_router"
    assert command.update["chat_response"] == "当前账号可访问 2 个北斗监测点。"


async def test_action_router_blocks_subscription_side_effects_until_hitl_exists() -> None:
    """Subscription actions are recognized but routed to render without executing side effects."""
    agent = LangGraphAgent()
    state = GraphState(
        messages=[HumanMessage(content="每天早上订阅这个站点的位移分析")],
        route="gnss",
        plan=AgentPlan(route="gnss", intent="subscription_action", needs_station=True),
        chat_response="已识别订阅请求。",
    )

    router_command = await agent._action_router(state)  # pyright: ignore[reportPrivateUsage]
    render_state = state.model_copy(update=router_command.update)
    render_command = await agent._render(render_state, _config())  # pyright: ignore[reportPrivateUsage]
    content = render_command.update["messages"][0].content

    assert router_command.goto == "render"
    assert router_command.update["action_type"] == "subscription_action"
    assert "不会执行订阅创建" in content


async def test_render_returns_chat_response() -> None:
    """Ordinary chat requests render the chat response directly."""
    agent = LangGraphAgent()
    state = GraphState(
        messages=[HumanMessage(content="讲个笑话")],
        route="chat",
        chat_response="这是普通 chat 回复。",
    )

    command = await agent._render(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "__end__"
    assert command.update["messages"][0].content == "这是普通 chat 回复。"
