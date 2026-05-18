from __future__ import annotations

import asyncio
from pathlib import Path

from my_agent.agent import AgentLoop
from my_agent.harness import AgentConfig, ToolRegistry
from my_agent.middleware import LoopLimitMiddleware, ThreadDataMiddleware, ToolErrorHandlingMiddleware
from my_agent.models import MockModelClient
from my_agent.runtime import JsonCheckpointStore, StreamWriter
from my_agent.tools import build_deerflow_search_tools


async def main() -> None:
    registry = ToolRegistry()
    for tool in build_deerflow_search_tools():
        registry.register(tool)

    stream = StreamWriter(lambda event: print(f"[event] {event.type}: {event.data}"))
    agent = AgentLoop(
        MockModelClient(),
        registry,
        config=AgentConfig(max_tool_iterations=2),
        middlewares=[
            ThreadDataMiddleware(root_dir=Path(".my-agent")),
            ToolErrorHandlingMiddleware(),
            LoopLimitMiddleware(),
        ],
        checkpoint_store=JsonCheckpointStore(".my-agent"),
        stream=stream,
    )
    state = await agent.run("demo-thread", "search latest BrowserGym usage")
    print("\nFINAL:", state.final)
    print("MESSAGES:", len(state.messages))


if __name__ == "__main__":
    asyncio.run(main())

