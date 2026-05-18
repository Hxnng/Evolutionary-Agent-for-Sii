from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from my_agent.harness.types import Message, ToolCall


@dataclass(slots=True)
class ModelOutput:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    thought: str | None = None


class ModelClient(Protocol):
    async def generate(self, messages: list[Message], tools_schema: list[dict]) -> ModelOutput: ...

