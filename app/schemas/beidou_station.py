"""Schemas for Beidou station lookup and GNSS graph planning."""

from typing import (
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    computed_field,
    Field,
)

STATION_TYPE_LABELS: dict[int, str] = {
    1: "基准站",
    2: "移动站单点模式",
    3: "移动站 RTK 模式",
    4: "中继站",
}

STATION_STATUS_LABELS: dict[int, str] = {
    10: "正常",
    20: "离线",
    30: "告警",
    40: "故障",
}


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

    @computed_field
    @property
    def station_type_label(self) -> str | None:
        """Human-readable Beidou station type label."""
        return beidou_station_type_label(self.station_type)

    @computed_field
    @property
    def station_type_description(self) -> str | None:
        """Model-readable Beidou station type description."""
        return beidou_station_enum_description("监测点类型", self.station_type, self.station_type_label)

    @computed_field
    @property
    def station_status_label(self) -> str | None:
        """Human-readable Beidou station status label."""
        return beidou_station_status_label(self.station_status)

    @computed_field
    @property
    def station_status_description(self) -> str | None:
        """Model-readable Beidou station status description."""
        return beidou_station_enum_description("监测点状态", self.station_status, self.station_status_label)


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

    @computed_field
    @property
    def station_type_label(self) -> str | None:
        """Human-readable Beidou station type label."""
        return beidou_station_type_label(self.station_type)

    @computed_field
    @property
    def station_type_description(self) -> str | None:
        """Model-readable Beidou station type description."""
        return beidou_station_enum_description("监测点类型", self.station_type, self.station_type_label)

    @computed_field
    @property
    def station_status_label(self) -> str | None:
        """Human-readable Beidou station status label."""
        return beidou_station_status_label(self.station_status)

    @computed_field
    @property
    def station_status_description(self) -> str | None:
        """Model-readable Beidou station status description."""
        return beidou_station_enum_description("监测点状态", self.station_status, self.station_status_label)


class AgentPlan(BaseModel):
    """Structured planning result for the request planner node."""

    route: Literal["gnss", "unsupported"] = "unsupported"
    intent: Literal[
        "unsupported",
        "station_groups",
        "station_list",
        "station_lookup",
        "station_detail",
        "gnss_analysis",
        "report_pdf",
        "subscription_action",
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


def beidou_station_type_label(value: int | None) -> str | None:
    """Return the user-facing label for a Beidou StationType value."""
    if value is None:
        return None
    return STATION_TYPE_LABELS.get(value, f"未知类型({value})")


def beidou_station_status_label(value: int | None) -> str | None:
    """Return the user-facing label for a Beidou StationStatus value."""
    if value is None:
        return None
    return STATION_STATUS_LABELS.get(value, f"未知状态({value})")


def beidou_station_enum_description(field_name: str, value: int | None, label: str | None) -> str | None:
    """Return a compact description that preserves raw enum value and readable meaning."""
    if value is None:
        return None
    if label is None:
        return str(value)
    return f"{label}（{field_name}={value}）"
