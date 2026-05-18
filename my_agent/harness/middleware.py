from __future__ import annotations

from typing import Any

from my_agent.harness.types import AgentState, Observation, ToolCall, ToolResult


class AgentMiddleware:
    """DeerFlow-style lifecycle hooks for the non-LangGraph sequential loop."""

    name = "middleware"

    async def before_agent(self, state: AgentState) -> AgentState:
        return state

    async def before_model(self, state: AgentState) -> AgentState:
        return state

    async def after_model(self, state: AgentState, model_output: Any) -> Any:
        return model_output

    async def wrap_tool_call(self, state: AgentState, call: ToolCall, handler: Any) -> ToolResult:
        return await handler(call)

    async def after_tool(self, state: AgentState, call: ToolCall, observation: Observation) -> AgentState:
        return state

    async def after_agent(self, state: AgentState) -> AgentState:
        return state

