from __future__ import annotations

import asyncio
import inspect
import sys
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from my_agent.harness.types import ToolResult


DEERFLOW_HARNESS = Path("/root/autodl-tmp/auto_agent/deer-flow/backend/packages/harness")

SEARCH_TOOL_CANDIDATES = {
    "web_search": [
        "deerflow.community.tavily.tools:web_search_tool",
        "deerflow.community.ddg_search.tools:web_search_tool",
        "deerflow.community.serper.tools:web_search_tool",
        "deerflow.community.infoquest.tools:web_search_tool",
    ],
    "web_fetch": [
        "deerflow.community.jina_ai.tools:web_fetch_tool",
        "deerflow.community.firecrawl.tools:web_fetch_tool",
        "deerflow.community.infoquest.tools:web_fetch_tool",
    ],
    "image_search": [
        "deerflow.community.image_search.tools:image_search_tool",
    ],
    "exa_search": [
        "deerflow.community.exa.tools:web_search_tool",
        "deerflow.community.exa.tools:exa_search_tool",
    ],
}


def _ensure_deerflow_path() -> None:
    path = str(DEERFLOW_HARNESS)
    if DEERFLOW_HARNESS.exists() and path not in sys.path:
        sys.path.insert(0, path)


def _load_symbol(spec: str) -> Any:
    module_name, symbol = spec.split(":", 1)
    module = import_module(module_name)
    return getattr(module, symbol)


@dataclass
class DeerFlowSearchToolAdapter:
    name: str
    candidates: list[str]
    description: str

    async def __call__(self, **kwargs: Any) -> ToolResult:
        _ensure_deerflow_path()
        errors: list[str] = []
        for candidate in self.candidates:
            try:
                tool = _load_symbol(candidate)
            except Exception as exc:
                errors.append(f"{candidate}: load failed: {exc}")
                continue
            try:
                result = await self._invoke(tool, kwargs)
                return ToolResult(
                    content=str(result),
                    call_id=self.name,
                    name=self.name,
                    is_error=False,
                    metadata={"provider": candidate, "arguments": kwargs},
                )
            except Exception as exc:
                errors.append(f"{candidate}: call failed: {exc}")
        fallback = await self._fallback(kwargs, errors)
        if fallback is not None:
            return fallback
        return ToolResult(
            content=(
                f"Error: DeerFlow search adapter '{self.name}' could not execute. "
                "Ensure DeerFlow harness dependencies and provider API keys are configured.\n"
                + "\n".join(errors[-5:])
            ),
            call_id=self.name,
            name=self.name,
            is_error=True,
            metadata={"arguments": kwargs, "errors": errors},
        )

    async def _fallback(self, kwargs: dict[str, Any], errors: list[str]) -> ToolResult | None:
        if self.name in {"web_search", "image_search"}:
            return await asyncio.to_thread(self._ddgs_search, kwargs, errors)
        if self.name == "web_fetch":
            return await asyncio.to_thread(self._urllib_fetch, kwargs, errors)
        return None

    def _ddgs_search(self, kwargs: dict[str, Any], errors: list[str]) -> ToolResult:
        query = kwargs.get("query")
        if not query:
            return ToolResult(
                content="Error: fallback search requires argument 'query'.",
                call_id=self.name,
                name=self.name,
                is_error=True,
                metadata={"arguments": kwargs, "errors": errors},
            )
        max_results = int(kwargs.get("max_results", 3) or 3)
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                if self.name == "image_search":
                    results = list(ddgs.images(str(query), max_results=max_results))
                else:
                    results = list(ddgs.text(str(query), max_results=max_results))
        except Exception as exc:
            errors.append(f"ddgs fallback failed: {exc}")
            return ToolResult(
                content="Error: fallback DDGS search failed.\n" + "\n".join(errors[-6:]),
                call_id=self.name,
                name=self.name,
                is_error=True,
                metadata={"arguments": kwargs, "errors": errors},
            )

        lines = []
        for idx, item in enumerate(results, 1):
            title = item.get("title") or item.get("image") or "untitled"
            href = item.get("href") or item.get("url") or item.get("image") or ""
            body = item.get("body") or item.get("description") or ""
            lines.append(f"{idx}. {title}\nURL: {href}\nSnippet: {body}".strip())
        return ToolResult(
            content="\n\n".join(lines) if lines else "No search results.",
            call_id=self.name,
            name=self.name,
            is_error=False,
            metadata={"provider": "ddgs_fallback", "arguments": kwargs, "deerflow_errors": errors},
        )

    def _urllib_fetch(self, kwargs: dict[str, Any], errors: list[str]) -> ToolResult:
        url = kwargs.get("url")
        if not url:
            return ToolResult(
                content="Error: fallback fetch requires argument 'url'.",
                call_id=self.name,
                name=self.name,
                is_error=True,
                metadata={"arguments": kwargs, "errors": errors},
            )
        try:
            request = Request(str(url), headers={"User-Agent": "my-agent/0.1"})
            with urlopen(request, timeout=20) as response:
                content = response.read(20000).decode("utf-8", errors="replace")
        except Exception as exc:
            errors.append(f"urllib fallback failed: {exc}")
            return ToolResult(
                content="Error: fallback web_fetch failed.\n" + "\n".join(errors[-6:]),
                call_id=self.name,
                name=self.name,
                is_error=True,
                metadata={"arguments": kwargs, "errors": errors},
            )
        return ToolResult(
            content=content,
            call_id=self.name,
            name=self.name,
            is_error=False,
            metadata={"provider": "urllib_fallback", "arguments": kwargs, "deerflow_errors": errors},
        )

    async def _invoke(self, tool: Any, kwargs: dict[str, Any]) -> Any:
        target = getattr(tool, "ainvoke", None)
        if target is not None:
            return await target(kwargs)
        target = getattr(tool, "invoke", None)
        if target is not None:
            return await asyncio.to_thread(target, kwargs)
        if inspect.iscoroutinefunction(tool):
            return await tool(**kwargs)
        return await asyncio.to_thread(tool, **kwargs)


def build_deerflow_search_tools() -> list[DeerFlowSearchToolAdapter]:
    return [
        DeerFlowSearchToolAdapter(
            name=name,
            candidates=candidates,
            description=f"DeerFlow-compatible search tool adapter for {name}.",
        )
        for name, candidates in SEARCH_TOOL_CANDIDATES.items()
    ]
