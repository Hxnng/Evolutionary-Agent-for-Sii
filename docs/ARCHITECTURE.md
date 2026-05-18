# my-agent Architecture

## Goal

Build a compact personal agent runtime from these sources:

- DeerFlow harness concepts
- AutoGen sandbox execution
- BrowserGym environment tools
- LangGraph-inspired runtime persistence, without LangGraph graph/tool-chain execution

## Runtime Layers

```text
API / CLI
  -> AgentLoop
     -> Middleware chain
     -> ModelClient
     -> ToolRegistry
     -> SandboxExecutor
     -> CheckpointStore
     -> StreamWriter
```

## Why No LangGraph Tool Chain

This project does not use `StateGraph`, `ToolNode`, or `create_agent`.

The tool loop is intentionally explicit in `my_agent.agent.loop.AgentLoop`.
That makes it easier to experiment with AutoGen-style error observations and
BrowserGym environment steps without adopting LangGraph's Pregel runtime.

## What Is Preserved From DeerFlow/LangGraph

- Thread-scoped state.
- Checkpoint persistence.
- Stream events.
- Middleware lifecycle.
- Tool error observations.
- Sandbox lifecycle.
- Search tool grouping and provider adapter.

## AutoGen-Inspired Sandbox

`DockerSandboxExecutor` follows AutoGen's command-line executor design:

- create or reuse workspace
- bind workspace to `/workspace`
- write code blocks to files
- prevent filename path escape
- execute with `timeout`
- capture combined output and exit code
- stop container at lifecycle end

## DeerFlow Search Tools

`build_deerflow_search_tools()` preserves DeerFlow search capability as adapters.
It tries to import DeerFlow search tool symbols from the existing checkout. This
keeps search providers swappable while avoiding migration of unrelated DeerFlow
tools.

## BrowserGym

BrowserGym is represented as `BrowserGymSession` plus `BrowserGymTool`. A web
task remains an environment with `reset/step/close`, and the agent sees a normal
tool observation after each action.

