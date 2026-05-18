from __future__ import annotations

from typing import Any

from my_agent.harness.middleware import AgentMiddleware
from my_agent.harness.types import AgentState, ToolCall, ToolResult


class ToolErrorHandlingMiddleware(AgentMiddleware):
    name = "tool_error_handling"

    async def wrap_tool_call(self, state: AgentState, call: ToolCall, handler: Any) -> ToolResult:
        try:
            return await handler(call)
        except Exception as exc:
            detail = str(exc).strip() or exc.__class__.__name__
            if len(detail) > 1000:
                detail = detail[:997] + "..."
            return ToolResult(
                content=(
                    f"Error: Tool '{call.name}' failed with {exc.__class__.__name__}: {detail}. "
                    "Revise the arguments or choose another strategy."
                ),
                call_id=call.id,
                name=call.name,
                is_error=True,
                metadata={"arguments": call.arguments, "exception_type": exc.__class__.__name__},
            )

