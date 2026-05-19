"""Short-term and long-term memory access for the harness.

Short-term memory stores compact episodic traces from recent task runs.  It is
used by the curator as adaptive context for nearby failures/successes, but it
is not treated as a durable rule.

Long-term memory is represented by learned skill files in ``learned_skills`` and
managed by ``SkillStore``.  Keeping the two layers separate prevents context
bloat while still exposing enough recent trace signal for credit assignment.
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


def _tokens(text: str) -> set[str]:
    return {x.lower() for x in _TOKEN_RE.findall(text or "") if len(x.strip()) > 1}


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
    skill_updates_applied: list[dict[str, Any]] | None = None
    trajectory_path: str = ""

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
        tools = f"tools={self.tool_call_count}"
        repeats = f"repeats={self.repeated_tool_calls}"
        skills = ",".join(self.selected_skills[:4]) or "none"
        lesson = _compact(self.lesson, 180) if self.lesson else "no durable lesson yet"
        question = _compact(self.instruction, 160)
        return (
            f"- id={self.memory_id}; [{status}] family={self.family}; skills={skills}; {tools}; {repeats}; "
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
    """Store and retrieve short-term episodic memory.

    The durable long-term layer is the learned skill directory.  This class only
    owns recent episodic traces, bounded by retention and retrieval limits.
    """

    def __init__(self, learned_path: str | Path = "learned_skills") -> None:
        root = Path(__file__).resolve().parent
        raw = Path(learned_path)
        self.learned_path = raw if raw.is_absolute() else root / raw
        self.memory_dir = self.learned_path / "_memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.short_term_path = self.memory_dir / "short_term.jsonl"

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
            skill_updates_applied=skill_updates_applied or summary.get("skill_updates_applied") or [],
            trajectory_path=str(summary.get("path") or summary.get("trajectory_path") or ""),
        )
        with self.short_term_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")
        self._prune()

    def read_short_term(self) -> list[ShortTermMemory]:
        if not self.short_term_path.exists():
            return []
        rows: list[ShortTermMemory] = []
        with self.short_term_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(data, dict):
                    rows.append(
                        ShortTermMemory(
                            task_id=str(data.get("task_id") or ""),
                            timestamp=float(data.get("timestamp") or 0.0),
                            family=str(data.get("family") or ""),
                            success=bool(data.get("success")),
                            instruction=str(data.get("instruction") or ""),
                            pred=str(data.get("pred") or ""),
                            answer=str(data.get("answer") or ""),
                            selected_skills=[str(x) for x in (data.get("selected_skills") or [])],
                            tool_call_count=int(data.get("tool_call_count") or 0),
                            repeated_tool_calls=int(data.get("repeated_tool_calls") or 0),
                            reached_max_steps=bool(data.get("reached_max_steps")),
                            lesson=str(data.get("lesson") or ""),
                            skill_updates_applied=list(data.get("skill_updates_applied") or []),
                            trajectory_path=str(data.get("trajectory_path") or ""),
                        )
                    )
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
            "Recent bounded trajectory memories. These are diagnostic hints, not durable facts.",
            "",
        ]
        lines.extend(item.to_prompt_line() for item in rows)
        return "\n".join(lines).strip()

    def _prune(self) -> None:
        max_items = int(os.getenv("SHORT_TERM_MEMORY_MAX_ITEMS", "200"))
        rows = self.read_short_term()
        if len(rows) <= max_items:
            return
        rows = rows[-max_items:]
        with self.short_term_path.open("w", encoding="utf-8") as f:
            for item in rows:
                f.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")


def format_short_term_memories(items: list[ShortTermMemory]) -> str:
    if not items:
        return ""
    lines = [
        "## Short-Term Episodic Memory",
        "Use these recent traces only as routing/diagnostic hints. They are not facts for the current task and must not override current evidence.",
    ]
    lines.extend(item.to_prompt_line() for item in items)
    return "\n".join(lines).strip()
