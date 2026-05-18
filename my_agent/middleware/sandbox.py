from __future__ import annotations

from my_agent.harness.middleware import AgentMiddleware
from my_agent.harness.types import AgentState
from my_agent.sandbox.base import SandboxExecutor


class SandboxMiddleware(AgentMiddleware):
    name = "sandbox"

    def __init__(self, executor: SandboxExecutor) -> None:
        self.executor = executor

    async def before_agent(self, state: AgentState) -> AgentState:
        await self.executor.start()
        state.context["sandbox"] = self.executor
        return state

    async def after_agent(self, state: AgentState) -> AgentState:
        await self.executor.stop()
        return state

