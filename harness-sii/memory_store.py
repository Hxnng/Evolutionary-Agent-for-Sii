"""Readable memory layers for the self-evolving harness.

The harness has two memory layers with different contracts:

- Long-term memory is the durable learned skill library managed by
  ``SkillStore`` under ``learned_skills/{dataset}/``.
- Short-term memory is a bounded set of recent trajectory notes under
  ``learned_skills/_memory/short_term/*.md``.  These notes are diagnostic
  hints for curator routing and are never loaded as long-term skills.

Keeping both layers as Markdown keeps the memory bank inspectable while the
directory boundary keeps transient traces from becoming procedural skills.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
_SAFE_ID_RE = re.compile(r"[^0-9A-Za-z_.-]+")
_FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


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


def _slug(value: str) -> str:
    safe = _SAFE_ID_RE.sub("-", str(value or "").strip()).strip("-._").lower()
    return safe[:96] or f"memory-{int(time.time())}"


def _split_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[|,，、;；]+", str(value or ""))
    clean: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text and text not in clean:
            clean.append(text)
    return clean


def _parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "success"}


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text.strip()
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, text[match.end() :].strip()


def _section(body: str, heading: str) -> str:
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\n(.*?)(?=^## |\Z)")
    match = pattern.search(body or "")
    return match.group(1).strip() if match else ""


def _format_meta_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ", ".join(str(x).strip() for x in value if str(x).strip())
    return str(value or "").replace("\n", " ").strip()


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

    def to_prompt_line(self) -> str:
        status = "success" if self.success else "failure"
        skills = ",".join(self.selected_skills[:4]) or "none"
        lesson = _compact(self.lesson, 180) if self.lesson else "no durable lesson yet"
        question = _compact(self.instruction, 160)
        return (
            f"- id={self.memory_id}; [{status}] family={self.family}; skills={skills}; "
            f"tools={self.tool_call_count}; repeats={self.repeated_tool_calls}; "
            f"lesson={lesson}; task={question}"
        )

    def to_candidate(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "family": self.family,
            "success": self.success,
            "instruction": _compact(self.instruction, 220),
            "selected_skills": self.selected_skills[:5],
            "tool_call_count": self.tool_call_count,
            "repeated_tool_calls": self.repeated_tool_calls,
            "reached_max_steps": self.reached_max_steps,
            "lesson": _compact(self.lesson, 260),
        }


class MemoryStore:
    """Store and retrieve short-term episodic Markdown notes."""

    def __init__(self, learned_path: str | Path = "learned_skills") -> None:
        root = Path(__file__).resolve().parent
        raw = Path(learned_path)
        self.learned_path = raw if raw.is_absolute() else root / raw
        self.memory_dir = self.learned_path / "_memory"
        self.short_term_dir = self.memory_dir / "short_term"
        self.short_term_dir.mkdir(parents=True, exist_ok=True)

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
        path = self._path_for(entry)
        path.write_text(self._to_markdown(entry), encoding="utf-8")
        self._prune()

    def read_short_term(self) -> list[ShortTermMemory]:
        rows: list[ShortTermMemory] = []
        for path in sorted(self.short_term_dir.glob("*.md")):
            item = self._read_markdown(path)
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

    def _path_for(self, entry: ShortTermMemory) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(entry.timestamp))
        base = f"{stamp}-{_slug(entry.memory_id)}"
        path = self.short_term_dir / f"{base}.md"
        suffix = 1
        while path.exists():
            path = self.short_term_dir / f"{base}-{suffix:02d}.md"
            suffix += 1
        return path

    def _read_markdown(self, path: Path) -> ShortTermMemory | None:
        try:
            meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
        except OSError:
            return None
        try:
            timestamp = float(meta.get("timestamp") or path.stat().st_mtime)
        except (OSError, ValueError):
            timestamp = 0.0
        return ShortTermMemory(
            task_id=meta.get("task_id", ""),
            timestamp=timestamp,
            family=meta.get("family", ""),
            success=_parse_bool(meta.get("success", "false")),
            instruction=_section(body, "Task"),
            pred=_section(body, "Prediction"),
            answer=_section(body, "Gold Answer"),
            selected_skills=_split_list(meta.get("selected_skills")),
            tool_call_count=int(meta.get("tool_call_count") or 0),
            repeated_tool_calls=int(meta.get("repeated_tool_calls") or 0),
            reached_max_steps=_parse_bool(meta.get("reached_max_steps", "false")),
            lesson=_section(body, "Lesson"),
            skill_updates_applied=_split_list(meta.get("skill_updates_applied")),
            trajectory_path=meta.get("trajectory_path", ""),
            path=str(path),
        )

    def _to_markdown(self, entry: ShortTermMemory) -> str:
        meta = {
            "task_id": entry.task_id,
            "timestamp": f"{entry.timestamp:.6f}",
            "family": entry.family,
            "success": entry.success,
            "selected_skills": entry.selected_skills,
            "tool_call_count": entry.tool_call_count,
            "repeated_tool_calls": entry.repeated_tool_calls,
            "reached_max_steps": entry.reached_max_steps,
            "skill_updates_applied": entry.skill_updates_applied or [],
            "trajectory_path": entry.trajectory_path,
        }
        front = "\n".join(f"{key}: {_format_meta_value(value)}" for key, value in meta.items())
        return (
            f"---\n{front}\n---\n"
            f"# Short-Term Memory: {entry.memory_id}\n\n"
            "This is a bounded episodic note for curator routing. It is not a long-term skill and must not be treated as task evidence.\n\n"
            f"## Task\n{entry.instruction.strip()}\n\n"
            f"## Lesson\n{entry.lesson.strip() or 'No stable lesson recorded.'}\n\n"
            f"## Prediction\n{entry.pred.strip()}\n\n"
            f"## Gold Answer\n{entry.answer.strip()}\n"
        )

    def _prune(self) -> None:
        max_items = int(os.getenv("SHORT_TERM_MEMORY_MAX_ITEMS", "200"))
        rows = self.read_short_term()
        if len(rows) <= max_items:
            return
        for item in rows[: len(rows) - max_items]:
            path = Path(item.path)
            if path.exists() and self.short_term_dir.resolve() in path.resolve().parents:
                path.unlink()


def format_short_term_memories(items: list[ShortTermMemory]) -> str:
    if not items:
        return ""
    lines = [
        "## Short-Term Episodic Memory",
        "Use these recent Markdown notes only as routing/diagnostic hints. They are not facts for the current task and must not override current evidence.",
    ]
    lines.extend(item.to_prompt_line() for item in items)
    return "\n".join(lines).strip()
