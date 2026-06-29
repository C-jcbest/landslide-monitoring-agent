"""Schemas for Beidou station lookup and GNSS graph planning."""

from typing import (
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
)


class BeidouSession(BaseModel):
    """Current user's Beidou upstream session."""

    session_uuid: str = Field(..., min_length=1)


class BeidouStationGroup(BaseModel):
    """Normalized Beidou station group."""

    station_group_uuid: str
    station_group_name: str
    station_count: int = 0
    station_group_desc: str | None = None


class BeidouPageInfo(BaseModel):
    """Normalized Beidou pagination metadata."""

    page_flag: str | None = None
    page_number: int | None = None
    page_size: int | None = None
    total_number: int | None = None


class BeidouStation(BaseModel):
    """Normalized Beidou station detail."""

    station_group_uuid: str | None = None
    station_group_name: str | None = None
    station_uuid: str
    device_uuid: str | None = None
    station_name: str
    station_n0: str | None = None
    station_e0: str | None = None
    station_u0: str | None = None
    station_type: int | None = None
    station_location: str | None = None
    station_status: int | None = None
    station_desc: str | None = None
    base_station_uuid: str | None = None
    base_station_name: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    altitude: str | None = None


class StationCandidate(BaseModel):
    """Narrow station candidate projection safe to send to the LLM."""

    station_uuid: str
    station_name: str
    station_group_name: str | None = None
    device_uuid: str | None = None
    station_type: int | None = None
    station_status: int | None = None
    station_location: str | None = None
    base_station_name: str | None = None


class AgentPlan(BaseModel):
    """Structured planning result for the Plan node."""

    route: Literal["chat", "gnss_analysis"] = "chat"
    intent: Literal[
        "chat",
        "weather",
        "station_groups",
        "station_list",
        "station_lookup",
        "station_detail",
        "gnss_analysis",
        "unknown",
    ] = "unknown"
    station_mentions: list[str] = Field(default_factory=list)
    possible_codes: list[str] = Field(default_factory=list)
    context_reference: bool = False
    needs_station: bool = False
    needs_weather: bool = False
    reason: str = ""


class GateDecision(BaseModel):
    """Structured candidate decision for the Gate node."""

    status: Literal["ready", "auth_missing", "needs_clarification", "no_candidate", "upstream_error"] = (
        "needs_clarification"
    )
    resolved_station_uuid: str | None = None
    confidence: Literal["high", "medium", "low"] = "low"
    clarification_question: str | None = None
    candidate_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class AnalyzeExecutionResult(BaseModel):
    """Structured ExecuteAnalyze result."""

    status: Literal["ok", "auth_missing", "station_not_found", "upstream_error"] = "ok"
    intent: str = "station_detail"
    station: BeidouStation | None = None
    station_groups: list[BeidouStationGroup] = Field(default_factory=list)
    station_candidates: list[StationCandidate] = Field(default_factory=list)
    weather: dict[str, Any] | None = None
    message: str | None = None


def station_to_candidate(station: BeidouStation) -> StationCandidate:
    """Project a full station detail into the narrow LLM-safe candidate shape."""
    return StationCandidate(
        station_uuid=station.station_uuid,
        station_name=station.station_name,
        station_group_name=station.station_group_name,
        device_uuid=station.device_uuid,
        station_type=station.station_type,
        station_status=station.station_status,
        station_location=station.station_location,
        base_station_name=station.base_station_name,
    )
