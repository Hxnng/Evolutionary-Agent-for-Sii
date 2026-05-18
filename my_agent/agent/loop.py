from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from my_agent.harness.middleware import AgentMiddleware
from my_agent.harness.registry import ToolRegistry
from my_agent.harness.types import AgentConfig, AgentState, Message, Observation, ToolCall, ToolResult
from my_agent.models.base import ModelClient, ModelOutput
from my_agent.runtime.checkpoint import JsonCheckpointStore
from my_agent.runtime.stream import StreamWriter


class AgentLoop:
    """Explicit model/tool loop. No LangGraph StateGraph or ToolNode dependency."""

    def __init__(
        self,
        model: ModelClient,
        registry: ToolRegistry,
        *,
        config: AgentConfig | None = None,
        middlewares: Iterable[AgentMiddleware] = (),
        checkpoint_store: JsonCheckpointStore | None = None,
        stream: StreamWriter | None = None,
    ) -> None:
        self.model = model
        self.registry = registry
        self.config = config or AgentConfig()
        self.middlewares = list(middlewares)
        self.checkpoint_store = checkpoint_store
        self.stream = stream or StreamWriter()

    async def run(self, thread_id: str, user_input: str, *, context: dict[str, Any] | None = None) -> AgentState:
        state = None
        if self.checkpoint_store is not None:
            state = await self.checkpoint_store.get(thread_id)
        if state is None:
            state = AgentState(thread_id=thread_id, context=context or {})
            if self.config.system_prompt:
                state.messages.append(Message(role="system", content=self.config.system_prompt))
        elif context:
            state.context.update(context)

        state.messages.append(Message(role="user", content=user_input))

        for mw in self.middlewares:
            state = await mw.before_agent(state)

        consecutive_errors = 0
        for iteration in range(self.config.max_tool_iterations):
            self.stream.write("model_start", iteration=iteration)
            for mw in self.middlewares:
                state = await mw.before_model(state)

            output = await self.model.generate(state.messages, self._tool_schema())
            for mw in reversed(self.middlewares):
                output = await mw.after_model(state, output)

            if not isinstance(output, ModelOutput):
                raise TypeError(f"after_model middleware must return ModelOutput, got {type(output).__name__}")

            self.stream.write(
                "model_end",
                iteration=iteration,
                content=output.content,
                thought=output.thought,
                tool_calls=[
                    {"id": call.id, "name": call.name, "arguments": call.arguments}
                    for call in output.tool_calls
                ],
            )

            if output.content:
                state.messages.append(Message(role="assistant", content=output.content))

            if not output.tool_calls:
                state.final = output.content
                state.halted = True
                self.stream.write("agent_final", content=output.content)
                break

            for call in output.tool_calls:
                if "max_results" not in call.arguments and call.name in {"web_search", "image_search", "exa_search"}:
                    call.arguments["max_results"] = 3
                self.stream.write("tool_start", id=call.id, name=call.name, arguments=call.arguments)
                result = await self._execute_tool_with_middlewares(state, call)
                observation = Observation(
                    content=result.content,
                    call_id=result.call_id,
                    source=result.name,
                    is_error=result.is_error,
                    raw=result.metadata,
                )
                state.observations.append(observation)
                state.messages.append(observation.to_message())
                for mw in reversed(self.middlewares):
                    state = await mw.after_tool(state, call, observation)
                self.stream.write(
                    "tool_end",
                    id=call.id,
                    name=call.name,
                    is_error=result.is_error,
                    content=result.content,
                    metadata=result.metadata,
                )
                consecutive_errors = consecutive_errors + 1 if result.is_error else 0

            if state.halted:
                self.stream.write("agent_halted", reason="middleware_halted")
                break

            if self.config.max_consecutive_tool_errors > 0 and consecutive_errors >= self.config.max_consecutive_tool_errors:
                state.final = "Stopped after consecutive tool errors."
                state.halted = True
                self.stream.write("agent_halted", reason="max_consecutive_tool_errors")
                break
        else:
            state.final = "Stopped after reaching max_tool_iterations."
            state.halted = True
            self.stream.write("agent_halted", reason="max_tool_iterations")

        for mw in reversed(self.middlewares):
            state = await mw.after_agent(state)

        if self.checkpoint_store is not None:
            await self.checkpoint_store.put(state)
        return state

    async def _execute_tool_with_middlewares(self, state: AgentState, call: ToolCall) -> ToolResult:
        async def terminal_handler(inner_call: ToolCall) -> ToolResult:
            tool = self.registry.get(inner_call.name)
            if tool is None:
                return ToolResult(
                    content=f"Error: tool '{inner_call.name}' not found",
                    call_id=inner_call.id,
                    name=inner_call.name,
                    is_error=True,
                    metadata={"arguments": inner_call.arguments},
                )
            return await tool(**inner_call.arguments)

        handler = terminal_handler
        for mw in reversed(self.middlewares):
            next_handler = handler

            async def wrapped(inner_call: ToolCall, mw: AgentMiddleware = mw, next_handler: Any = next_handler) -> ToolResult:
                return await mw.wrap_tool_call(state, inner_call, next_handler)

            handler = wrapped
        return await handler(call)

    def _tool_schema(self) -> list[dict]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self.registry.list()
        ]
