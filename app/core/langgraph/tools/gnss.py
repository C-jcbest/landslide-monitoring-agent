"""Read-only GNSS tool schemas for the LangGraph agent."""

import json
from typing import Any

from langchain_core.tools import StructuredTool
from langchain_core.tools.base import BaseTool
from pydantic import (
    BaseModel,
    Field,
)


class EmptyGnssToolInput(BaseModel):
    """No-argument GNSS tool input."""


class StationDetailToolInput(BaseModel):
    """Input for reading a Beidou station detail."""

    station_uuid: str = Field(..., min_length=1, description="当前用户可访问的北斗站点 UUID。")


async def _tool_requires_graph_context(**_: Any) -> str:
    """Return a safe error if a GNSS tool is invoked outside the graph node."""
    return json.dumps(
        {
            "ok": False,
            "error_code": "graph_context_required",
            "message": "该 GNSS 工具只能在受控图节点内读取当前用户上下文后执行。",
        },
        ensure_ascii=False,
    )


get_beidou_station_groups_tool = StructuredTool.from_function(
    coroutine=_tool_requires_graph_context,
    name="get_beidou_station_groups",
    description="读取当前用户可访问的北斗站点分组列表。只读工具，不接受或暴露 SessionUUID。",
    args_schema=EmptyGnssToolInput,
)

get_beidou_station_candidates_tool = StructuredTool.from_function(
    coroutine=_tool_requires_graph_context,
    name="get_beidou_station_candidates",
    description="读取当前用户可访问的北斗站点候选列表，用于站点消歧、列表和数量查询。只读工具。",
    args_schema=EmptyGnssToolInput,
)

get_beidou_station_detail_tool = StructuredTool.from_function(
    coroutine=_tool_requires_graph_context,
    name="get_beidou_station_detail",
    description="按 station_uuid 读取当前用户可访问的北斗站点详情。只读工具。",
    args_schema=StationDetailToolInput,
)

get_beidou_station_weather_tool = StructuredTool.from_function(
    coroutine=_tool_requires_graph_context,
    name="get_beidou_station_weather",
    description="按 station_uuid 读取站点经纬度并查询天气事实，用于降雨和 GNSS 分析。只读工具。",
    args_schema=StationDetailToolInput,
)

gnss_read_only_tools: list[BaseTool] = [
    get_beidou_station_groups_tool,
    get_beidou_station_candidates_tool,
    get_beidou_station_detail_tool,
    get_beidou_station_weather_tool,
]
