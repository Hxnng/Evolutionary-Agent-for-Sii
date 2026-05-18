from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4


def new_thread_id() -> str:
    return str(uuid4())


@dataclass(slots=True)
class ThreadContext:
    thread_id: str
    root_dir: Path
    metadata: dict = field(default_factory=dict)

    @property
    def workspace(self) -> Path:
        path = self.root_dir / "threads" / self.thread_id / "workspace"
        path.mkdir(parents=True, exist_ok=True)
        return path

