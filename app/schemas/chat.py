"""This file contains the chat schema for the application."""

import re
from typing import (
    Any,
    List,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.schemas.base import BaseResponse


class Message(BaseModel):
    """Message model for chat endpoint.

    Attributes:
        role: The role of the message sender (user or assistant).
        content: The content of the message.
    """

    model_config = {"extra": "ignore"}

    role: Literal["user", "assistant", "system"] = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The content of the message", min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate the message content.

        Args:
            v: The content to validate

        Returns:
            str: The validated content

        Raises:
            ValueError: If the content contains disallowed patterns
        """
        # Check for potentially harmful content
        if re.search(r"<script.*?>.*?</script>", v, re.IGNORECASE | re.DOTALL):
            raise ValueError("Content contains potentially harmful script tags")

        # Check for null bytes
        if "\0" in v:
            raise ValueError("Content contains null bytes")

        return v


class ChatRequest(BaseModel):
    """Request model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
    """

    messages: List[Message] = Field(
        ...,
        description="List of messages in the conversation",
        min_length=1,
    )


class ChatResponse(BaseResponse):
    """Response model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
    """

    messages: List[Message] = Field(..., description="List of messages in the conversation")
    is_interrupted: bool = Field(
        default=False, description="Whether the conversation is currently interrupted/waiting for human input"
    )
    interrupt_question: Optional[str] = Field(
        default=None, description="The question/prompt from the active interrupt"
    )


class StreamResponse(BaseResponse):
    """Response model for streaming chat endpoint.

    Attributes:
        content: The content of the current chunk.
        done: Whether the stream is complete.
    """

    event: Literal["token", "tool_start", "tool_end", "error", "done"] = Field(
        default="token",
        description="The stream event type",
    )
    content: str = Field(default="", description="The content of the current chunk")
    done: bool = Field(default=False, description="Whether the stream is complete")
    tool_name: Optional[str] = Field(default=None, description="The tool name for tool events")
    tool_input: Optional[dict[str, Any]] = Field(default=None, description="The tool input for tool events")
    error: Optional[str] = Field(default=None, description="The error message for error events")


class SessionTitle(BaseModel):
    """Structured output schema for session title generation."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=60,
    )

    @field_validator("title")
    @classmethod
    def _normalize(cls, v: str) -> str:
        v = " ".join(v.split()).strip(" \"'`.,:;!?-")
        if not v:
            raise ValueError("empty title after normalization")
        return v
