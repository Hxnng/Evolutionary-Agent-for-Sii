from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


Role = Literal["system", "user", "assistant", "tool", "observation"]


@dataclass(slots=True)
class Message:
    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class ToolResult:
    content: str
    call_id: str
    name: str
    is_error: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Observation:
    """Model-visible tool/code execution observation."""

    content: str
    call_id: str
    source: str
    is_error: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> Message:
        return Message(
            role="observation",
            content=self.content,
            name=self.source,
            tool_call_id=self.call_id,
            metadata={"is_error": self.is_error, "raw": self.raw},
        )


@dataclass(slots=True)
class AgentState:
    thread_id: str
    messages: list[Message] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    halted: bool = False
    final: str | None = None


@dataclass(slots=True)
class AgentConfig:
    name: str = "lead_agent"
    max_tool_iterations: int = 6
    max_consecutive_tool_errors: int = 3
    system_prompt: str = "You are a pragmatic agent. Use tools only when they materially help."


class Tool(Protocol):
    name: str
    description: str

    async def __call__(self, **kwargs: Any) -> ToolResult: ...


ToolFunc = Callable[..., Awaitable[ToolResult]]

