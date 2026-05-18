from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class CodeBlock:
    code: str
    language: str = "python"
    filename: str | None = None


@dataclass(slots=True)
class CodeResult:
    exit_code: int
    output: str
    code_file: str | None = None
    timed_out: bool = False


class SandboxExecutor(Protocol):
    work_dir: Path

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def restart(self) -> None: ...
    async def execute(self, blocks: list[CodeBlock]) -> CodeResult: ...

