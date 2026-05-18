from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

from my_agent.sandbox.base import CodeBlock, CodeResult
from my_agent.sandbox.common import language_to_command, safe_code_filename


class DockerSandboxExecutor:
    """AutoGen-style Docker command-line sandbox.

    It binds a host workspace into `/workspace`, writes model code to files,
    executes through `docker exec`, captures combined output and exit code,
    and enforces a POSIX timeout inside the container.
    """

    def __init__(
        self,
        image: str = "python:3-slim",
        *,
        work_dir: str | Path | None = None,
        timeout: int = 60,
        container_name: str | None = None,
        auto_remove: bool = True,
    ) -> None:
        self.image = image
        self.timeout = timeout
        self.container_name = container_name or f"my-agent-code-exec-{uuid.uuid4()}"
        self.auto_remove = auto_remove
        self._tmp: TemporaryDirectory[str] | None = None
        self.work_dir = Path(work_dir) if work_dir else Path()
        self._container = None
        self._running = False

    async def start(self) -> None:
        try:
            import docker
            from docker.errors import ImageNotFound, NotFound
        except ImportError as exc:
            raise RuntimeError("Install docker extra first: pip install 'my-agent[docker]'") from exc

        if not self.work_dir:
            self._tmp = TemporaryDirectory()
            self.work_dir = Path(self._tmp.name)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        client = docker.from_env()
        try:
            await asyncio.to_thread(client.images.get, self.image)
        except ImageNotFound:
            await asyncio.to_thread(client.images.pull, self.image)

        try:
            existing = await asyncio.to_thread(client.containers.get, self.container_name)
            await asyncio.to_thread(existing.remove, force=True)
        except NotFound:
            pass

        self._container = await asyncio.to_thread(
            client.containers.create,
            self.image,
            name=self.container_name,
            entrypoint="/bin/sh",
            tty=True,
            detach=True,
            auto_remove=self.auto_remove,
            volumes={str(self.work_dir.resolve()): {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
        )
        await asyncio.to_thread(self._container.start)
        self._running = True

    async def stop(self) -> None:
        if self._container is not None and self._running:
            try:
                await asyncio.to_thread(self._container.stop)
            finally:
                self._running = False
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None

    async def restart(self) -> None:
        if self._container is None:
            await self.start()
            return
        await asyncio.to_thread(self._container.restart)

    async def execute(self, blocks: list[CodeBlock]) -> CodeResult:
        if self._container is None or not self._running:
            raise RuntimeError("Docker sandbox is not running")
        outputs: list[str] = []
        last_exit = 0
        first_file: str | None = None
        for block in blocks:
            filename = safe_code_filename(block.code, block.language, self.work_dir, block.filename)
            path = self.work_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(block.code, encoding="utf-8")
            first_file = first_file or str(path)
            command = ["timeout", str(self.timeout), language_to_command(block.language), filename]
            result = await asyncio.to_thread(self._container.exec_run, command)
            last_exit = int(result.exit_code)
            text = result.output.decode("utf-8", errors="replace")
            if last_exit == 124:
                text += "\nTimeout"
            outputs.append(text)
            if last_exit != 0:
                break
        return CodeResult(exit_code=last_exit, output="".join(outputs), code_file=first_file, timed_out=last_exit == 124)

