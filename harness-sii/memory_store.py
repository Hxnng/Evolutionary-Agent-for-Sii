"""Decoupled memory storage for the self-evolving harness.

Memory uses two Markdown files with different loading paths:

- ``learned_skills/general/memory.md`` is the long-term memory skill. It can be
  selected as durable procedure guidance.
- ``learned_skills/_memory/short_term.md`` is a bounded short-term diagnostic
  file. The leading underscore keeps it out of skill retrieval; curator reads
  only a few relevant rows through ``MemoryStore.retrieve_short_term``.

This keeps the mental model simple while preserving the rule that current-task
evidence overrides both memory files.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
_SHORT_TERM_RECORD_RE = re.compile(r"<!--\s*short_term_memory:\s*(.*?)\s*-->", re.DOTALL)
_SHORT_TERM_HEADING = "## Entries"
_SOURCE_DIGEST_RE = re.compile(r"source_digest:\s*([^\n]+)")
_ATOMIC_FACT_RE = re.compile(r"(?:atomic_fact|图像识别线索 atomic_fact):\s*([^\n]+)")
_SKILL_ROUTE_RE = re.compile(r"skill_route:\s*([^\n]+)")
_DEFAULT_MEMORY_BODY = """## Long-Term Memory
Use this section for stable, reusable task-solving procedures. Keep it short,
actionable, and free of one-off answers or benchmark facts.

### 适用触发 / When to use
- Use memory when no narrower learned skill clearly matches the task risk.
- Prefer current evidence, dataset hints, and tool results over memory.

### 失败诊断 / Credit assignment
- Before changing strategy, decide whether the risk is evidence selection,
  tool use, reasoning composition, stop condition, or answer format.
- Only convert a repeated pattern into long-term guidance when it changes a
  future context or tool decision.

### 上下文/证据选择流程
- Identify the requested answer type before using tools: entity, attribute,
  date, count, location, yes/no, comparison, or multi-hop target.
- Extract the core entity and relation, then name the exact evidence gap.
- Use compact evidence first; call tools only for unresolved gaps.

### 工具计划
- Use the smallest tool plan that can close the evidence gap.
- Prefer one high-signal query over repeated broad searches.

### 停止/回退条件
- Stop when evidence directly resolves the requested answer span.
- If tool results repeat or contradict low-confidence memory, fall back to the
  best current evidence and preserve uncertainty in the reasoning process.

### 输出格式风险
- Preserve the requested granularity, language, unit, and wrapper.
- Do not mention memory, skills, curator context, or trajectory in the final
  answer.
"""
_DEFAULT_SHORT_TERM_TEXT = """# Short-Term Memory

Recent bounded trajectory notes for curator routing. This file is not a skill,
is not loaded with Long-Term Memory, and must not be treated as task evidence.

## Entries
"""


def _tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in _TOKEN_RE.findall(text or ""):
        token = raw.lower().strip()
        if len(token) <= 1:
            continue
        tokens.add(token)
        for part in re.split(r"[_-]+", token):
            if len(part) > 1:
                tokens.add(part)
        cjk_chars = [char for char in token if "\u4e00" <= char <= "\u9fff"]
        for idx in range(len(cjk_chars) - 1):
            tokens.add("".join(cjk_chars[idx : idx + 2]))
    return tokens


def _compact(value: Any, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


@dataclass
class ShortTermMemory:
    task_id: str
    timestamp: float
    family: str
    success: bool
    instruction: str
    pred: str
    answer: str
    selected_skills: list[str]
    tool_call_count: int = 0
    repeated_tool_calls: int = 0
    reached_max_steps: bool = False
    lesson: str = ""
    skill_updates_applied: list[str] | None = None
    trajectory_path: str = ""
    path: str = ""

    @property
    def memory_id(self) -> str:
        return self.task_id or str(int(self.timestamp))

    def searchable_text(self) -> str:
        return " ".join(
            [
                self.family,
                self.instruction,
                self.pred,
                self.answer,
                self.lesson,
                " ".join(self.selected_skills),
            ]
        )

    def compact_task_hint(self) -> str:
        parts: list[str] = []
        first_line = str(self.instruction or "").splitlines()[0].strip()
        if first_line:
            parts.append(_compact(first_line, 80))
        for label, pattern in (
            ("fact", _ATOMIC_FACT_RE),
            ("source", _SOURCE_DIGEST_RE),
            ("route", _SKILL_ROUTE_RE),
        ):
            match = pattern.search(self.instruction or "")
            if match:
                parts.append(f"{label}={_compact(match.group(1), 60)}")
        return "; ".join(parts) or "no task hint"

    def to_prompt_line(self) -> str:
        status = "success" if self.success else "failure"
        lesson = _compact(self.lesson, 120) if self.lesson else "no lesson"
        return (
            f"- id={self.memory_id}; {status}; family={self.family or 'unknown'}; "
            f"risk={lesson}; hint={self.compact_task_hint()}"
        )

    def to_candidate(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "family": self.family,
            "success": self.success,
            "task_hint": self.compact_task_hint(),
            "tool_call_count": self.tool_call_count,
            "repeated_tool_calls": self.repeated_tool_calls,
            "reached_max_steps": self.reached_max_steps,
            "lesson": _compact(self.lesson, 160),
        }


class MemoryStore:
    """Store and retrieve short-term notes in a separate non-skill file."""

    def __init__(self, learned_path: str | Path = "learned_skills") -> None:
        root = Path(__file__).resolve().parent
        raw = Path(learned_path)
        self.learned_path = raw if raw.is_absolute() else root / raw
        self.memory_skill_path = self.learned_path / "general" / "memory.md"
        self.short_term_path = self.learned_path / "_memory" / "short_term.md"
        self.memory_skill_path.parent.mkdir(parents=True, exist_ok=True)
        self.short_term_path.parent.mkdir(parents=True, exist_ok=True)

    def append_short_term(
        self,
        *,
        task: dict[str, Any],
        summary: dict[str, Any],
        lesson: str = "",
        skill_updates_applied: list[dict[str, Any]] | None = None,
    ) -> None:
        if os.getenv("ENABLE_SHORT_TERM_MEMORY", "1") != "1":
            return
        entry = ShortTermMemory(
            task_id=str(summary.get("task_id") or task.get("id") or ""),
            timestamp=time.time(),
            family=str(summary.get("curator_family") or ""),
            success=bool(summary.get("success")),
            instruction=str(summary.get("instruction") or task.get("instruction") or ""),
            pred=str(summary.get("pred") or ""),
            answer=str(summary.get("answer") or task.get("answer") or ""),
            selected_skills=[str(x) for x in (summary.get("selected_skills") or [])],
            tool_call_count=int(summary.get("tool_call_count") or 0),
            repeated_tool_calls=int(summary.get("repeated_tool_calls") or 0),
            reached_max_steps=bool(summary.get("reached_max_steps")),
            lesson=str(lesson or ""),
            skill_updates_applied=[
                str(update.get("skill_id") or update)
                for update in (skill_updates_applied or summary.get("skill_updates_applied") or [])
            ],
            trajectory_path=str(summary.get("path") or summary.get("trajectory_path") or ""),
        )
        self._append_to_short_term_file(entry)
        self._prune()

    def read_short_term(self) -> list[ShortTermMemory]:
        rows: list[ShortTermMemory] = []
        text = self._read_short_term_text()
        for match in _SHORT_TERM_RECORD_RE.finditer(text):
            item = self._record_to_memory(match.group(1))
            if item:
                rows.append(item)
        rows.sort(key=lambda item: item.timestamp)
        return rows

    def retrieve_short_term(
        self,
        query: str,
        *,
        family: str | None = None,
        k: int = 3,
        min_score: float | None = None,
    ) -> list[ShortTermMemory]:
        if os.getenv("ENABLE_SHORT_TERM_MEMORY", "1") != "1":
            return []
        threshold = float(os.getenv("SHORT_TERM_MEMORY_MIN_SCORE", "1.8")) if min_score is None else float(min_score)
        query_tokens = _tokens(query)
        now = time.time()
        scored: list[tuple[float, ShortTermMemory]] = []
        for item in self.read_short_term():
            if family and item.family and item.family != family:
                continue
            overlap = len(query_tokens & _tokens(item.searchable_text()))
            if overlap <= 0:
                continue
            age_hours = max(0.0, (now - item.timestamp) / 3600.0)
            recency = max(0.0, 1.0 - age_hours / max(1.0, float(os.getenv("SHORT_TERM_MEMORY_DECAY_HOURS", "72"))))
            failure_bonus = 0.35 if not item.success else 0.10
            tool_bonus = min(0.4, 0.08 * item.tool_call_count)
            score = overlap + recency + failure_bonus + tool_bonus
            if score >= threshold:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[: max(0, int(k))]]

    def short_term_manifest_text(self, *, limit: int = 12) -> str:
        rows = self.read_short_term()[-max(0, int(limit)) :]
        if not rows:
            return "# Short-Term Episodic Memory\n\n- No short-term memories yet."
        lines = [
            "# Short-Term Episodic Memory",
            "",
            "Recent bounded trajectory notes. These are diagnostic hints, not durable facts or skills.",
            "",
        ]
        lines.extend(item.to_prompt_line() for item in rows)
        return "\n".join(lines).strip()

    def _read_memory_skill_text(self) -> str:
        if self.memory_skill_path.exists():
            return self.memory_skill_path.read_text(encoding="utf-8")
        return self._default_memory_skill_text()

    def _default_memory_skill_text(self) -> str:
        front = "\n".join(
            [
                "skill_id: memory",
                "title: Long-Term Memory Skill",
                "domains: general, memory",
                "triggers: memory, fallback, context, evidence, format",
                "summary: Long-term memory skill for durable procedure guidance; short-term trajectory notes are stored separately.",
                "confidence: 0.65",
            ]
        )
        return f"---\n{front}\n---\n# Long-Term Memory Skill\n\n{_DEFAULT_MEMORY_BODY.strip()}\n"

    def _write_memory_skill_text(self, text: str) -> None:
        self.memory_skill_path.write_text(text.rstrip() + "\n", encoding="utf-8")

    def _read_short_term_text(self) -> str:
        if self.short_term_path.exists():
            return self.short_term_path.read_text(encoding="utf-8")
        return _DEFAULT_SHORT_TERM_TEXT

    def _write_short_term_text(self, text: str) -> None:
        self.short_term_path.write_text(text.rstrip() + "\n", encoding="utf-8")

    def _append_to_short_term_file(self, entry: ShortTermMemory) -> None:
        text = self._read_short_term_text()
        if _SHORT_TERM_HEADING not in text:
            text = text.rstrip() + "\n\n" + _SHORT_TERM_HEADING + "\n"
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
        payload = json.dumps(self._memory_to_record(entry), ensure_ascii=False, sort_keys=True)
        visible = entry.to_prompt_line()
        addition = f"\n<!-- short_term_memory: {payload} -->\n- {stamp} {visible}\n"
        text = text.rstrip() + addition
        self._write_short_term_text(text)

    def _memory_to_record(self, entry: ShortTermMemory) -> dict[str, Any]:
        return {
            "task_id": entry.task_id,
            "timestamp": entry.timestamp,
            "family": entry.family,
            "success": entry.success,
            "task_hint": entry.compact_task_hint(),
            "selected_skills": entry.selected_skills,
            "tool_call_count": entry.tool_call_count,
            "repeated_tool_calls": entry.repeated_tool_calls,
            "reached_max_steps": entry.reached_max_steps,
            "lesson": _compact(entry.lesson, 180),
            "skill_updates_applied": entry.skill_updates_applied or [],
        }

    def _record_to_memory(self, raw: str) -> ShortTermMemory | None:
        try:
            meta = json.loads(raw)
        except json.JSONDecodeError:
            return None
        try:
            timestamp = float(meta.get("timestamp") or 0.0)
        except (TypeError, ValueError):
            timestamp = 0.0
        return ShortTermMemory(
            task_id=str(meta.get("task_id") or ""),
            timestamp=timestamp,
            family=str(meta.get("family") or ""),
            success=bool(meta.get("success")),
            instruction=str(meta.get("instruction") or meta.get("task_hint") or ""),
            pred=str(meta.get("pred") or ""),
            answer=str(meta.get("answer") or ""),
            selected_skills=[str(x) for x in (meta.get("selected_skills") or [])],
            tool_call_count=int(meta.get("tool_call_count") or 0),
            repeated_tool_calls=int(meta.get("repeated_tool_calls") or 0),
            reached_max_steps=bool(meta.get("reached_max_steps")),
            lesson=str(meta.get("lesson") or ""),
            skill_updates_applied=[str(x) for x in (meta.get("skill_updates_applied") or [])],
            trajectory_path=str(meta.get("trajectory_path") or ""),
            path=str(self.short_term_path),
        )

    def _prune(self) -> None:
        max_items = int(os.getenv("SHORT_TERM_MEMORY_MAX_ITEMS", "200"))
        rows = self.read_short_term()
        if len(rows) <= max_items:
            return
        kept_records = rows[-max_items:]
        text = self._read_short_term_text()
        prefix = text.split(_SHORT_TERM_HEADING, 1)[0].rstrip()
        short_lines = [
            _SHORT_TERM_HEADING,
            "Recent trajectory notes live here as bounded diagnostics. They are not facts",
            "for the current task and should never override current evidence.",
        ]
        for entry in kept_records:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
            payload = json.dumps(self._memory_to_record(entry), ensure_ascii=False, sort_keys=True)
            short_lines.append(f"\n<!-- short_term_memory: {payload} -->")
            short_lines.append(f"- {stamp} {entry.to_prompt_line()}")
        self._write_short_term_text(prefix + "\n\n" + "\n".join(short_lines))


def format_short_term_memories(items: list[ShortTermMemory]) -> str:
    if not items:
        return ""
    lines = [
        "## Short-Term Episodic Memory",
        "Use these recent Markdown notes only as routing/diagnostic hints. They are not facts for the current task and must not override current evidence.",
    ]
    lines.extend(item.to_prompt_line() for item in items)
    return "\n".join(lines).strip()
