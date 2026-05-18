from __future__ import annotations

from dataclasses import dataclass, field

from my_agent.harness.types import Tool


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def list(self) -> list[Tool]:
        return list(self.tools.values())

