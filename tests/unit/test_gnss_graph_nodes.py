"""Unit tests for the fixed five-node GNSS graph workflow."""

from typing import Any

import pytest
from langchain_core.messages import HumanMessage

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.beidou_station import (
    AgentPlan,
    BeidouSession,
    BeidouStation,
    BeidouStationGroup,
    GateDecision,
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
        station_n0="4421290.4231",
        station_e0="198942.5203",
        station_u0="17.2676",
        station_type=3,
        station_location="北坡一号滑坡体",
        station_status=10,
        station_desc="北坡 GNSS 监测点",
        base_station_uuid="33333333-3333-4333-8333-333333333333",
        base_station_name="北坡基准站",
        latitude="39.759630522",
        longitude="116.986252277",
        altitude="44.2287",
    )


class FakeLLMService:
    """LLM fake returning queued structured outputs and chat messages."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def call(self, messages: Any, **kwargs: Any) -> Any:
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return self.responses.pop(0)

    def get_llm(self) -> Any:
        return None

    def bind_tools(self, _: list[Any]) -> "FakeLLMService":
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


def _candidate(uuid: str = STATION_UUID, name: str = "北坡 GNSS 01") -> StationCandidate:
    return StationCandidate(
        station_uuid=uuid,
        station_name=name,
        station_group_name="北坡监测组",
        device_uuid="DEV-BP-001",
        station_type=3,
        station_status=10,
        station_location="北坡一号滑坡体",
        base_station_name="北坡基准站",
    )


def _config(user_id: str | None = "101") -> dict[str, Any]:
    metadata = {"session_id": "session-101", "username": "tester"}
    if user_id is not None:
        metadata["user_id"] = user_id
    return {"configurable": {"thread_id": "session-101"}, "metadata": metadata}


async def test_plan_routes_plain_weather_to_chat_without_station_gate() -> None:
    """Plain weather questions stay on the Chat branch and do not require Beidou station gates."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService(
        [
            AgentPlan(
                route="chat",
                intent="weather",
                station_mentions=[],
                possible_codes=[],
                context_reference=False,
                needs_station=False,
                needs_weather=True,
                reason="用户只询问天气。",
            )
        ]
    )
    state = GraphState(messages=[HumanMessage(content="今天有雨吗？")])

    command = await agent._plan(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "chat"
    assert command.update["route"] == "chat"
    assert command.update["plan"].needs_weather


async def test_gate_returns_auth_missing_without_calling_station_service() -> None:
    """GNSS requests without a Beidou session stop at Gate and go to Response."""
    agent = LangGraphAgent()
    agent.beidou_session_provider = FakeSessionProvider(None)
    agent.beidou_station_service = FakeStationService([_candidate()])
    state = GraphState(
        messages=[HumanMessage(content="分析北坡 GNSS 01")],
        route="gnss_analysis",
        plan=AgentPlan(route="gnss_analysis", intent="station_detail", needs_station=True),
    )

    command = await agent._gate(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "response"
    assert command.update["gate"].status == "auth_missing"
    assert agent.beidou_station_service.candidate_calls == 0


async def test_gate_allows_only_high_confidence_candidate_owned_by_current_user() -> None:
    """Gate trusts LLM semantics only after deterministic ownership and confidence checks."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService(
        [
            GateDecision(
                status="ready",
                resolved_station_uuid=STATION_UUID,
                confidence="high",
                candidate_ids=[STATION_UUID],
                reason="用户明确指向北坡 GNSS 01。",
            )
        ]
    )
    agent.beidou_session_provider = FakeSessionProvider(BeidouSession(session_uuid=SESSION_UUID))
    agent.beidou_station_service = FakeStationService([_candidate()])
    state = GraphState(
        messages=[HumanMessage(content="查北坡 GNSS 01 详情")],
        route="gnss_analysis",
        plan=AgentPlan(route="gnss_analysis", intent="station_detail", needs_station=True),
    )

    command = await agent._gate(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "execute_analyze"
    assert command.update["resolved_station"].station_uuid == STATION_UUID
    assert command.update["station_candidates"][0].station_uuid == STATION_UUID


async def test_gate_allows_station_group_query_after_authorization_only() -> None:
    """Station group listing needs authorization but does not need station disambiguation."""
    agent = LangGraphAgent()
    agent.beidou_session_provider = FakeSessionProvider(BeidouSession(session_uuid=SESSION_UUID))
    agent.beidou_station_service = FakeStationService([_candidate()])
    state = GraphState(
        messages=[HumanMessage(content="列出我的北斗站点分组")],
        route="gnss_analysis",
        plan=AgentPlan(route="gnss_analysis", intent="station_groups", needs_station=False),
    )

    command = await agent._gate(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "execute_analyze"
    assert command.update["gate"].status == "ready"
    assert agent.beidou_station_service.candidate_calls == 0


async def test_execute_analyze_returns_station_groups() -> None:
    """ExecuteAnalyze can return station group facts for an authorized user."""
    agent = LangGraphAgent()
    station_service = FakeStationService([_candidate()])
    agent.beidou_session_provider = FakeSessionProvider(BeidouSession(session_uuid=SESSION_UUID))
    agent.beidou_station_service = station_service
    state = GraphState(
        messages=[HumanMessage(content="列出我的北斗站点分组")],
        route="gnss_analysis",
        plan=AgentPlan(route="gnss_analysis", intent="station_groups", needs_station=False),
    )

    command = await agent._execute_analyze(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "response"
    assert station_service.group_calls == 1
    assert command.update["execution_result"].station_groups[0].station_group_name == "北坡监测组"


async def test_gate_downgrades_medium_confidence_to_clarification() -> None:
    """A medium-confidence LLM preference must not execute monitoring analysis."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService(
        [
            GateDecision(
                status="ready",
                resolved_station_uuid=STATION_UUID,
                confidence="medium",
                candidate_ids=[STATION_UUID, OTHER_STATION_UUID],
                reason="候选名称接近。",
            )
        ]
    )
    agent.beidou_session_provider = FakeSessionProvider(BeidouSession(session_uuid=SESSION_UUID))
    agent.beidou_station_service = FakeStationService(
        [_candidate(STATION_UUID, "北坡 GNSS 01"), _candidate(OTHER_STATION_UUID, "北坡 GNSS 02")]
    )
    state = GraphState(
        messages=[HumanMessage(content="查北坡站")],
        route="gnss_analysis",
        plan=AgentPlan(route="gnss_analysis", intent="station_detail", needs_station=True),
    )

    command = await agent._gate(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "response"
    assert command.update["gate"].status == "needs_clarification"
    assert "北坡 GNSS 01" in command.update["gate"].clarification_question


async def test_gate_rejects_llm_station_uuid_outside_current_user_candidates() -> None:
    """LLM output cannot select a station that was not returned for the current user."""
    agent = LangGraphAgent()
    agent.llm_service = FakeLLMService(
        [
            GateDecision(
                status="ready",
                resolved_station_uuid=OTHER_STATION_UUID,
                confidence="high",
                candidate_ids=[OTHER_STATION_UUID],
                reason="模型选择了外部 UUID。",
            )
        ]
    )
    agent.beidou_session_provider = FakeSessionProvider(BeidouSession(session_uuid=SESSION_UUID))
    agent.beidou_station_service = FakeStationService([_candidate()])
    state = GraphState(
        messages=[HumanMessage(content="查这个站点")],
        route="gnss_analysis",
        plan=AgentPlan(route="gnss_analysis", intent="station_detail", needs_station=True),
    )

    command = await agent._gate(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "response"
    assert command.update["gate"].status == "needs_clarification"
    assert command.update["resolved_station"] is None


async def test_execute_analyze_can_add_weather_only_after_gate_resolved_station() -> None:
    """Weather facts are read inside ExecuteAnalyze after station authorization and confirmation."""
    agent = LangGraphAgent()
    station_service = FakeStationService([_candidate()])
    weather_service = FakeWeatherService()
    agent.beidou_session_provider = FakeSessionProvider(BeidouSession(session_uuid=SESSION_UUID))
    agent.beidou_station_service = station_service
    agent.weather_service = weather_service
    state = GraphState(
        messages=[HumanMessage(content="结合最近降雨分析北坡 GNSS 01")],
        route="gnss_analysis",
        plan=AgentPlan(route="gnss_analysis", intent="gnss_analysis", needs_station=True, needs_weather=True),
        resolved_station=_candidate(),
    )

    command = await agent._execute_analyze(state, _config())  # pyright: ignore[reportPrivateUsage]

    assert command.goto == "response"
    assert station_service.detail_calls == [STATION_UUID]
    assert weather_service.calls == [STATION_UUID]
    assert command.update["execution_result"].weather["rain_summary"]["recent_24h_precipitation"] == 18.6


async def test_response_renders_candidate_clarification() -> None:
    """Response assembles a user-facing clarification without exposing credentials."""
    agent = LangGraphAgent()
    state = GraphState(
        messages=[HumanMessage(content="查北坡站")],
        route="gnss_analysis",
        station_candidates=[_candidate(STATION_UUID, "北坡 GNSS 01"), _candidate(OTHER_STATION_UUID, "北坡 GNSS 02")],
        gate=GateDecision(
            status="needs_clarification",
            confidence="low",
            candidate_ids=[STATION_UUID, OTHER_STATION_UUID],
            clarification_question="请确认要查询哪个站点。",
        ),
    )

    command = await agent._response(state, _config())  # pyright: ignore[reportPrivateUsage]
    content = command.update["messages"][0].content

    assert command.goto == "__end__"
    assert "请确认要查询哪个站点" in content
    assert "北坡 GNSS 01" in content
    assert SESSION_UUID not in content
