from __future__ import annotations

from pathlib import Path

from my_agent.harness.middleware import AgentMiddleware
from my_agent.harness.types import AgentState
from my_agent.runtime.thread import ThreadContext


class ThreadDataMiddleware(AgentMiddleware):
    name = "thread_data"

    def __init__(self, root_dir: str | Path = ".my-agent") -> None:
        self.root_dir = Path(root_dir)

    async def before_agent(self, state: AgentState) -> AgentState:
        ctx = ThreadContext(thread_id=state.thread_id, root_dir=self.root_dir)
        state.context["thread"] = ctx
        state.context["workspace"] = str(ctx.workspace)
        return state

