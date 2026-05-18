from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from my_agent.sandbox.base import CodeBlock, CodeResult
from my_agent.sandbox.common import language_to_command, safe_code_filename


class LocalSandboxExecutor:
    """Development-only executor. Prefer DockerSandboxExecutor for untrusted code."""

    def __init__(self, work_dir: str | Path | None = None, timeout: int = 60) -> None:
        self._tmp: TemporaryDirectory[str] | None = None
        self.work_dir = Path(work_dir) if work_dir else Path()
        self.timeout = timeout

    async def start(self) -> None:
        if not self.work_dir:
            self._tmp = TemporaryDirectory()
            self.work_dir = Path(self._tmp.name)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    async def stop(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None

    async def restart(self) -> None:
        await self.stop()
        await self.start()

    async def execute(self, blocks: list[CodeBlock]) -> CodeResult:
        outputs: list[str] = []
        last_exit = 0
        first_file: str | None = None
        for block in blocks:
            filename = safe_code_filename(block.code, block.language, self.work_dir, block.filename)
            code_path = self.work_dir / filename
            code_path.parent.mkdir(parents=True, exist_ok=True)
            code_path.write_text(block.code, encoding="utf-8")
            first_file = first_file or str(code_path)
            proc = await asyncio.create_subprocess_exec(
                "timeout",
                str(self.timeout),
                language_to_command(block.language),
                str(code_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await proc.communicate()
            last_exit = proc.returncode or 0
            text = out.decode("utf-8", errors="replace")
            if last_exit == 124:
                text += "\nTimeout"
            outputs.append(text)
            if last_exit != 0:
                break
        return CodeResult(exit_code=last_exit, output="".join(outputs), code_file=first_file, timed_out=last_exit == 124)

