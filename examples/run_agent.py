from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from my_agent.agent import AgentLoop
from my_agent.config import build_model_client_from_env, env_bool, env_int, load_env_file
from my_agent.harness import AgentConfig, ToolRegistry
from my_agent.middleware import LoopLimitMiddleware, ThreadDataMiddleware, ToolErrorHandlingMiddleware
from my_agent.runtime import JsonCheckpointStore, StreamWriter
from my_agent.sandbox import LocalSandboxExecutor
from my_agent.tools import CodeExecutionTool, build_deerflow_search_tools


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run my-agent with .env-selected model backend.")
    parser.add_argument("prompt", help="User prompt to send to the agent.")
    parser.add_argument("--thread-id", default="local-debug", help="Checkpoint thread id.")
    parser.add_argument("--env-file", default=".env", help="Path to local environment file.")
    args = parser.parse_args()

    load_env_file(args.env_file)

    registry = ToolRegistry()
    if env_bool("ENABLE_SEARCH_TOOLS", False):
        for tool in build_deerflow_search_tools():
            registry.register(tool)
    if env_bool("ENABLE_CODE_EXECUTION", False):
        registry.register(CodeExecutionTool(LocalSandboxExecutor(work_dir=Path(".my-agent/workspace"))))

    runtime_home = Path(".my-agent")
    stream = StreamWriter(lambda event: print(f"[event] {event.type}: {event.data}"))
    agent = AgentLoop(
        build_model_client_from_env(),
        registry,
        config=AgentConfig(
            max_tool_iterations=env_int("AGENT_MAX_TOOL_ITERATIONS", 4),
            max_consecutive_tool_errors=env_int("AGENT_MAX_CONSECUTIVE_TOOL_ERRORS", 2),
        ),
        middlewares=[
            ThreadDataMiddleware(root_dir=runtime_home),
            ToolErrorHandlingMiddleware(),
            LoopLimitMiddleware(),
        ],
        checkpoint_store=JsonCheckpointStore(runtime_home),
        stream=stream,
    )
    state = await agent.run(args.thread_id, args.prompt)
    print("\nFINAL:", state.final)


if __name__ == "__main__":
    asyncio.run(main())
