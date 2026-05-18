from __future__ import annotations

from my_agent.harness.middleware import AgentMiddleware
from my_agent.harness.types import AgentState, Observation, ToolCall


class LoopLimitMiddleware(AgentMiddleware):
    name = "loop_limit"

    def __init__(self, max_repeated_error_source: int = 2) -> None:
        self.max_repeated_error_source = max_repeated_error_source

    async def after_tool(self, state: AgentState, call: ToolCall, observation: Observation) -> AgentState:
        if not observation.is_error:
            return state
        recent = [o for o in state.observations[-self.max_repeated_error_source :] if o.source == observation.source and o.is_error]
        if len(recent) >= self.max_repeated_error_source:
            state.halted = True
            state.final = f"Stopped because tool '{observation.source}' repeatedly failed."
        return state

