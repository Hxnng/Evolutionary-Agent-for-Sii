"""
Structured memory for the evolutionary harness.

The store is intentionally simple: append-only JSONL for auditability plus
lightweight keyword retrieval for prompt injection.  It records both useful
success patterns and failure reflections, then exposes the most relevant
items to later tasks.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
_SENT_SPLIT_RE = re.compile(r"[。；;.!?\n]+")


def _tokens(text: str) -> set[str]:
    text = text or ""
    toks = {t.lower() for t in _TOKEN_RE.findall(text) if len(t.strip()) > 1}
    # Chinese questions are often short and not whitespace segmented.  Adding
    # single CJK characters gives the retrieval layer useful overlap without
    # adding a heavyweight tokenizer dependency.
    toks.update(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    return toks


def _compact(text: Any, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _first_sentence(text: str, limit: int = 90) -> str:
    text = str(text or "").strip()
    parts = [p.strip() for p in _SENT_SPLIT_RE.split(text) if p.strip()]
    return _compact(parts[0] if parts else text, limit=limit)


def _memory_kind(memory: dict[str, Any]) -> str:
    text = " ".join(str(memory.get(k, "")) for k in ("instruction", "lesson", "strategy", "tags"))
    rules = [
        ("format", ("格式", "量词", "年份", "日期", "第", "输出", "answer")),
        ("atomic", ("atomic_fact", "原子", "线索", "高置信", "直接")),
        ("artifact", ("文物", "朝代", "时代", "断代", "青铜", "瓷器", "钱币")),
        ("landmark", ("景观", "地标", "桥", "塔", "省份", "城市", "地点")),
        ("ocr", ("书", "作者", "字体", "期刊", "海报", "OCR")),
        ("tool", ("搜索", "工具", "浏览器", "search", "browser", "图搜")),
    ]
    for name, needles in rules:
        if any(n in text for n in needles):
            return name
    return "general"


def _compress_memory(memory: dict[str, Any]) -> dict[str, str]:
    kind = _memory_kind(memory)
    lesson = str(memory.get("lesson", "")).strip()
    strategy = str(memory.get("strategy", "")).strip()
    action = _first_sentence(strategy or lesson, limit=int(os.getenv("MEMORY_ITEM_CHARS", "90")))
    if not action:
        return {}
    stale_image_retry = (
        "图像识别工具" in action
        and ("重新调用" in action or "image_path" in action)
    ) or "0x0" in action
    if stale_image_retry:
        kind = "tool"
        action = "图搜/上传失败时不要反复调用 search_image；改用 atomic_fact、source_digest 或 search_text 查询实体属性"
    outcome = str(memory.get("outcome", "unknown"))
    tags = memory.get("tags", [])
    if isinstance(tags, list):
        tag_text = ",".join(str(t) for t in tags[:3])
    else:
        tag_text = str(tags)
    return {
        "kind": kind,
        "outcome": outcome,
        "tags": _compact(tag_text, limit=36),
        "action": action,
    }


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
        fingerprint = self._fingerprint(record)
        if fingerprint:
            record["fingerprint"] = fingerprint
            recent = self.read_all()[-80:]
            if any(row.get("fingerprint") == fingerprint for row in recent):
                return
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def _fingerprint(record: dict[str, Any]) -> str:
        core = " ".join(
            str(record.get(key, ""))
            for key in ("outcome", "lesson", "strategy", "tags")
        )
        toks = sorted(_tokens(core))
        return "|".join(toks[:80])

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
        query_lower = (query or "").lower()
        query_family = ""
        if "2wikimultihopqa" in query_lower or "candidate context:" in query_lower:
            query_family = "2wiki"
        elif "图像" in query or "image" in query_lower:
            query_family = "simplevqa"

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
            tags = {str(x).lower() for x in row.get("tags", [])}
            family_bonus = 1.5 if query_family and query_family in tags else 0.0
            specificity_text = str(row.get("lesson", "")) + str(row.get("strategy", ""))
            specificity_bonus = min(len(_tokens(specificity_text)) / 60, 1.0)
            scored.append((overlap + outcome_bonus + family_bonus + specificity_bonus + recency, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [row for _, row in scored[: max(0, int(k))]]


def format_memories_for_prompt(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return ""
    max_items = max(0, int(os.getenv("MEMORY_PROMPT_K", "4")))
    lines = [
        "## Compact Memory",
        "Only reusable tactics; not facts for the current question.",
    ]
    seen: set[str] = set()
    emitted = 0
    for memory in memories:
        item = _compress_memory(memory)
        if not item:
            continue
        fingerprint = f"{item['kind']}:{item['action'][:42]}"
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        emitted += 1
        lines.append(
            f"- [{item['kind']}/{item['outcome']}] {item['action']}"
        )
        if emitted >= max_items:
            break
    if emitted == 0:
        return ""
    return "\n".join(lines).strip()
