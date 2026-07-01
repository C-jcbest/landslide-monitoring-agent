"""LangGraph tools for enhanced language model capabilities.

This package contains custom tools that can be used with LangGraph to extend
the capabilities of language models. Currently includes tools for web search
and other external integrations.
"""

from langchain_core.tools.base import BaseTool

from .ask_human import ask_human
from .duckduckgo_search import duckduckgo_search_tool
from .gnss import gnss_read_only_tools
from .open_meteo_weather import query_open_meteo_weather_tool

chat_tools: list[BaseTool] = [duckduckgo_search_tool, query_open_meteo_weather_tool]
read_only_tools: list[BaseTool] = chat_tools
gnss_tools: list[BaseTool] = gnss_read_only_tools
tools: list[BaseTool] = [*read_only_tools, ask_human]
