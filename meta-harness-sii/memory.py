"""
Structured memory for the evolutionary harness.

The store is intentionally simple: append-only JSONL for auditability plus
lightweight keyword retrieval for prompt injection.  It records both useful
success patterns and failure reflections, then exposes the most relevant
items to later tasks.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def _tokens(text: str) -> set[str]:
    text = text or ""
    toks = {t.lower() for t in _TOKEN_RE.findall(text) if len(t.strip()) > 1}
    # Chinese questions are often short and not whitespace segmented.  Adding
    # single CJK characters gives the retrieval layer useful overlap without
    # adding a heavyweight tokenizer dependency.
    toks.update(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    return toks


@dataclass
class MemoryItem:
    task_id: str
    instruction: str
    outcome: str
    lesson: str
    strategy: str
    tags: list[str] = field(default_factory=list)
    answer: str = ""
    pred: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


class MemoryStore:
    """Append-only long-term memory with deterministic retrieval."""

    def __init__(self, path: str | Path = "memory/long_term_memory.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, item: MemoryItem | dict[str, Any]) -> None:
        record = item.to_record() if isinstance(item, MemoryItem) else dict(item)
        record.setdefault("timestamp", time.time())
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in self.read_all():
            haystack = " ".join(
                str(row.get(key, ""))
                for key in ("instruction", "lesson", "strategy", "tags", "answer", "pred")
            )
            overlap = len(query_tokens & _tokens(haystack))
            if overlap <= 0:
                continue
            recency = float(row.get("timestamp", 0.0)) / 1_000_000_000_000
            outcome_bonus = 0.3 if row.get("outcome") == "success" else 0.1
            scored.append((overlap + outcome_bonus + recency, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [row for _, row in scored[: max(0, int(k))]]


def format_memories_for_prompt(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return ""
    lines = [
        "## 可复用经验记忆",
        "以下内容只作为工具使用和解题策略建议，不是当前题目的事实证据；若与当前搜索/页面结果冲突，必须以当前工具证据为准。",
    ]
    for i, memory in enumerate(memories, start=1):
        outcome = memory.get("outcome", "unknown")
        lesson = str(memory.get("lesson", "")).strip()
        strategy = str(memory.get("strategy", "")).strip()
        if not lesson and not strategy:
            continue
        lines.append(f"{i}. outcome={outcome}; lesson={lesson}; strategy={strategy}")
    return "\n".join(lines).strip()
