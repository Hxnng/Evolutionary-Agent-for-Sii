from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from my_agent.harness.types import Message, ToolCall
from my_agent.models.base import ModelOutput

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None


IMAGE_MARKER_RE = re.compile(r"^IMAGE_PATH:\s*(?P<path>.+)$", re.MULTILINE)


class OpenAICompatibleAgentModelClient:
    """OpenAI-compatible chat client with prompt-level tool-call JSON parsing.

    The same client works for DashScope/Bailian compatible-mode APIs and local
    OpenAI-compatible servers such as vLLM. Provider-specific options can be
    passed through ``extra_body``.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        api_key_env: str | None = "OPENAI_API_KEY",
        timeout: int = 180,
        enable_thinking: bool | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stream: bool = True,
        extra_body: dict[str, Any] | None = None,
        provider_name: str = "OpenAI-compatible",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.enable_thinking = enable_thinking
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.stream = stream
        self.extra_body = extra_body or {}
        self.provider_name = provider_name

    async def generate(self, messages: list[Message], tools_schema: list[dict]) -> ModelOutput:
        payload = {
            "model": self.model,
            "messages": self._convert_messages(messages, tools_schema),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
        }
        if self.enable_thinking is not None:
            payload["enable_thinking"] = self.enable_thinking
        if self.extra_body:
            payload["extra_body"] = self.extra_body
        if self.stream:
            content, reasoning = self._post_stream(payload)
        else:
            result = self._post(payload)
            message = result["choices"][0]["message"]
            content = (message.get("content") or "").strip()
            reasoning = message.get("reasoning_content")
        return self._parse_model_content(content, reasoning)

    def _convert_messages(self, messages: list[Message], tools_schema: list[dict]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        tool_prompt = self._tool_prompt(tools_schema)
        for index, message in enumerate(messages):
            role = message.role
            if role == "observation":
                converted.append(
                    {
                        "role": "user",
                        "content": f"<tool_observation name={message.name!r} is_error={message.metadata.get('is_error')}>\n{message.content}\n</tool_observation>",
                    }
                )
                continue

            if role == "tool":
                converted.append({"role": "user", "content": f"<tool_result>\n{message.content}\n</tool_result>"})
                continue

            content = message.content
            if role == "system" and index == 0:
                content = content.rstrip() + "\n\n" + tool_prompt
                converted.append({"role": "system", "content": content})
                continue

            if role == "user":
                image_path = self._extract_image_path(content)
                text = IMAGE_MARKER_RE.sub("", content).strip()
                if image_path is not None:
                    converted.append({"role": "user", "content": self._multimodal_content(text, image_path)})
                    continue

            converted.append({"role": role if role in {"system", "user", "assistant"} else "user", "content": content})
        return converted

    def _tool_prompt(self, tools_schema: list[dict]) -> str:
        tool_lines = "\n".join(f"- {tool['name']}: {tool.get('description', '')}" for tool in tools_schema)
        return f"""
<my_agent_tool_protocol>
You are running inside my_agent AgentLoop. You may use tools when they improve accuracy.

Available tools:
{tool_lines if tool_lines else "- No tools available"}

Tool argument conventions:
- web_search: {{"query": "...", "max_results": 3}}
- web_fetch: {{"url": "..."}}
- image_search: {{"query": "...", "max_results": 3}}
- exa_search: {{"query": "...", "max_results": 3}}
- execute_code: {{"code": "...", "language": "python"}}

If you need tools, output ONLY valid JSON in this shape:
{{"tool_calls":[{{"name":"web_search","arguments":{{"query":"...","max_results":3}}}}]}}

After tool observations, either call another tool with the same JSON format or finish with:
{{"final":"short final answer"}}

For SimpleVQA, use the image first. Use tools only when external factual lookup, OCR checking, or code inspection can materially improve the answer.
The final answer must be short and contain no explanation.
</my_agent_tool_protocol>
"""

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(f"Missing API key. Set {self.api_key_env or 'api_key'}.")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        context = ssl.create_default_context(cafile=certifi.where()) if certifi is not None else None
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{self.provider_name} HTTP {exc.code}: {body or exc.reason}") from exc

    def _post_stream(self, payload: dict[str, Any]) -> tuple[str, str | None]:
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(f"Missing API key. Set {self.api_key_env or 'api_key'}.")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        context = ssl.create_default_context(cafile=certifi.where()) if certifi is not None else None
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        data = ""
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if chunk.get("error"):
                        raise RuntimeError(f"{self.provider_name} stream error: {chunk['error']}")
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    if delta.get("reasoning_content") is not None:
                        reasoning_parts.append(delta["reasoning_content"])
                    if delta.get("content"):
                        content_parts.append(delta["content"])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{self.provider_name} stream returned invalid JSON line: {data[:500]}") from exc
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{self.provider_name} HTTP {exc.code}: {body or exc.reason}") from exc
        return "".join(content_parts).strip(), "".join(reasoning_parts).strip() or None

    def _api_key(self) -> str | None:
        if self.api_key_env:
            return os.getenv(self.api_key_env) or self.api_key
        return self.api_key

    def _parse_model_content(self, content: str, reasoning: str | None) -> ModelOutput:
        parsed = self._loads_json(content)
        if isinstance(parsed, dict):
            calls = parsed.get("tool_calls")
            if isinstance(calls, list) and calls:
                return ModelOutput(
                    content="",
                    thought=reasoning,
                    tool_calls=[
                        ToolCall(
                            id=f"dashscope-tool-{idx}",
                            name=str(call["name"]),
                            arguments=dict(call.get("arguments") or {}),
                        )
                        for idx, call in enumerate(calls)
                        if isinstance(call, dict) and call.get("name")
                    ],
                )
            if "final" in parsed:
                return ModelOutput(content=str(parsed["final"]).strip(), thought=reasoning)
        return ModelOutput(content=content, thought=reasoning)

    def _loads_json(self, content: str) -> Any:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _extract_image_path(self, content: str) -> Path | None:
        match = IMAGE_MARKER_RE.search(content)
        if not match:
            return None
        path = Path(match.group("path").strip())
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        return path

    def _multimodal_content(self, text: str, image_path: Path) -> list[dict[str, Any]]:
        mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
        ]


class DashScopeAgentModelClient(OpenAICompatibleAgentModelClient):
    """DashScope/Bailian convenience wrapper."""

    def __init__(
        self,
        *,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str,
        api_key: str | None = None,
        api_key_env: str | None = "DASHSCOPE_API_KEY",
        timeout: int = 180,
        enable_thinking: bool | None = True,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stream: bool = True,
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            model=model,
            api_key=api_key,
            api_key_env=api_key_env,
            timeout=timeout,
            enable_thinking=enable_thinking,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            extra_body=extra_body,
            provider_name="DashScope",
        )
