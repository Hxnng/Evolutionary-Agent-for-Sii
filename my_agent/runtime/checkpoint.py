from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from my_agent.harness.types import AgentState, Message, Observation


class JsonCheckpointStore:
    """Thread/checkpoint persistence inspired by LangGraph, without LangGraph dependency."""

    def __init__(self, root: str | Path = ".my-agent") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, thread_id: str) -> Path:
        path = self.root / "checkpoints"
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{thread_id}.json"

    async def put(self, state: AgentState) -> None:
        payload = asdict(state)
        payload["context"] = _json_safe(payload.get("context", {}))
        self._path(state.thread_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    async def get(self, thread_id: str) -> AgentState | None:
        path = self._path(thread_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return AgentState(
            thread_id=payload["thread_id"],
            messages=[Message(**m) for m in payload.get("messages", [])],
            observations=[Observation(**o) for o in payload.get("observations", [])],
            artifacts=payload.get("artifacts", []),
            context=payload.get("context", {}),
            halted=payload.get("halted", False),
            final=payload.get("final"),
        )


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"sandbox"}:
                continue
            safe[str(key)] = _json_safe(item)
        return safe
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return repr(value)
