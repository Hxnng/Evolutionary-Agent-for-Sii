from __future__ import annotations

from my_agent.harness.types import Message, ToolCall
from my_agent.models.base import ModelOutput


class MockModelClient:
    """Small deterministic client for local smoke tests."""

    async def generate(self, messages: list[Message], tools_schema: list[dict]) -> ModelOutput:
        if messages and messages[-1].role == "observation":
            obs = messages[-1]
            status = "failed" if obs.metadata.get("is_error") else "succeeded"
            return ModelOutput(content=f"Observed tool result from {obs.name}: {status}. {obs.content[:300]}")

        last = messages[-1].content if messages else ""
        if "search" in last.lower():
            return ModelOutput(
                tool_calls=[
                    ToolCall(id="mock-search-1", name="web_search", arguments={"query": last, "max_results": 3})
                ]
            )
        return ModelOutput(content=f"Mock final answer: {last}")
