"""This file contains the graph schema for the application."""

from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
)

from app.schemas.beidou_station import (
    AgentPlan,
    AnalyzeExecutionResult,
    GateDecision,
    StationCandidate,
)


class GraphState(BaseModel):
    """State definition for the LangGraph Agent/Workflow."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )
    long_term_memory: str = Field(default="", description="The long term memory of the conversation")
    route: str = Field(default="chat", description="The planned graph route")
    plan: AgentPlan | None = Field(default=None, description="Structured request plan")
    gate: GateDecision | None = Field(default=None, description="Structured gate decision")
    station_candidates: list[StationCandidate] = Field(default_factory=list, description="LLM-safe station candidates")
    resolved_station: StationCandidate | None = Field(default=None, description="Confirmed station candidate")
    execution_result: AnalyzeExecutionResult | None = Field(default=None, description="Analyze execution result")
    chat_response: str = Field(default="", description="Plain chat response assembled by Chat node")
