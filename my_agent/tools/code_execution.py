from __future__ import annotations

from dataclasses import dataclass

from my_agent.harness.types import ToolResult
from my_agent.sandbox.base import CodeBlock, SandboxExecutor


@dataclass
class CodeExecutionTool:
    executor: SandboxExecutor
    name: str = "execute_code"
    description: str = "Execute Python or shell code in the configured sandbox and return output plus exit code."

    async def __call__(self, code: str, language: str = "python", filename: str | None = None) -> ToolResult:
        result = await self.executor.execute([CodeBlock(code=code, language=language, filename=filename)])
        if result.output.strip():
            content = result.output
        else:
            content = f"The script ran but produced no output. Exit code: {result.exit_code}"
        if result.exit_code != 0:
            content = f"The script exited with POSIX code {result.exit_code}.\nOutput:\n{content}"
        return ToolResult(
            content=content,
            call_id="execute_code",
            name=self.name,
            is_error=result.exit_code != 0,
            metadata={
                "exit_code": result.exit_code,
                "code_file": result.code_file,
                "timed_out": result.timed_out,
            },
        )

