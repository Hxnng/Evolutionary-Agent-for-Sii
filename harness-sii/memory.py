"""
Markdown memory for the evolutionary harness.

The store is intentionally simple: append-only Markdown for model-friendly
context plus lightweight keyword retrieval for prompt injection.  It records
both useful success patterns and failure reflections, then exposes the most
relevant items to later tasks.  Legacy JSONL memory files are still readable so
old runs can be reused during migration.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

_MEMORY_APPEND_LOCK = threading.Lock()


_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
_SENT_SPLIT_RE = re.compile(r"[。；;.!?\n]+")
_MD_ENTRY_RE = re.compile(r"(?m)^## Memory(?:\s+\d+|: .*)$")
_MD_SECTION_RE = re.compile(r"(?m)^### ([A-Za-z][A-Za-z ]*)\s*$")
_MD_META_RE = re.compile(r"^- ([A-Za-z ]+):\s*(.*)$")
_STORE_HEADER = "# Long-Term Memory\n\n<!-- memory-store: markdown-v3 compact-failure -->\n\n"
_TAG_SPLIT_RE = re.compile(r"[|,，、/\s]+")
_ALLOWED_TAGS = {
    "format",
    "search",
    "browser",
    "tool",
    "ocr",
    "image",
    "entity",
    "multihop",
    "evidence",
    "efficiency",
    "reasoning",
}
_TAG_ALIASES = {
    "2wiki": "multihop",
    "2wikimultihopqa": "multihop",
    "simplevqa": "image",
    "atomic": "evidence",
    "atomic_fact": "evidence",
    "source": "evidence",
}


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


def _md_text(text: Any) -> str:
    text = str(text or "").strip()
    return text if text else "-"


def _md_inline(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip() or "-"


def _memory_limit(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _timestamp_to_iso(value: Any) -> str:
    try:
        return datetime.fromtimestamp(float(value)).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return datetime.fromtimestamp(time.time()).isoformat(timespec="seconds")


def _timestamp_from_iso(value: str) -> float:
    value = str(value or "").strip()
    if not value or value == "-":
        return 0.0
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return 0.0


def _format_tags(tags: Any) -> str:
    clean = _clean_tags(tags)
    return ", ".join(f"`{tag}`" for tag in clean) if clean else "-"


def _clean_tags(tags: Any) -> list[str]:
    raw_tags = tags if isinstance(tags, list) else [tags]
    clean: list[str] = []
    for raw in raw_tags:
        for part in _TAG_SPLIT_RE.split(str(raw or "").strip("` ").lower()):
            tag = _TAG_ALIASES.get(part, part)
            if tag not in _ALLOWED_TAGS or tag in clean:
                continue
            clean.append(tag)
            if len(clean) >= _memory_limit("MEMORY_TAGS_MAX", 3):
                return clean
    return clean


def _parse_tags(text: str) -> list[str]:
    text = str(text or "").strip()
    if not text or text == "-":
        return []
    tags = re.findall(r"`([^`]+)`", text)
    if tags:
        return [tag.strip() for tag in tags if tag.strip()]
    return [part.strip() for part in text.split(",") if part.strip()]


def _markdown_record(record: dict[str, Any], index: int | None = None) -> str:
    title = f"## Memory {index:03d}" if index is not None else "## Memory"
    return "\n".join(
        [
            title,
            "",
            f"- Task: {_md_inline(record.get('instruction'))}",
            f"- Tags: {_format_tags(record.get('tags', []))}",
            f"- Memory: {_md_inline(record.get('lesson'))}",
            "",
        ]
    )


def _compact_markdown_record(record: dict[str, Any]) -> dict[str, Any]:
    compact = dict(record)
    compact["instruction"] = _compact(
        _clean_task_text(compact.get("instruction")),
        limit=_memory_limit("MEMORY_TASK_CHARS", 120),
    )
    compact["lesson"] = _compact(
        _merge_memory_text(compact.get("lesson"), compact.get("strategy")),
        limit=_memory_limit("MEMORY_ITEM_CHARS", 160),
    )
    compact["strategy"] = ""
    compact["tags"] = _clean_tags(compact.get("tags", []))
    compact["answer"] = ""
    compact["pred"] = ""
    return compact


def _clean_task_text(text: Any) -> str:
    text = str(text or "").strip()
    cut_markers = [
        "可用数据集线索",
        "数据集线索",
        "candidate context:",
        "Candidate Context:",
    ]
    for marker in cut_markers:
        pos = text.find(marker)
        if pos > 0:
            text = text[:pos].strip()
    return text


def _merge_memory_text(lesson: Any, strategy: Any) -> str:
    lesson_text = _md_inline(lesson)
    strategy_text = _md_inline(strategy)
    if lesson_text == "-":
        return "" if strategy_text == "-" else strategy_text
    if strategy_text == "-" or strategy_text == lesson_text or strategy_text in lesson_text:
        return lesson_text
    if lesson_text in strategy_text:
        return strategy_text
    return f"{lesson_text} {strategy_text}"


def _parse_markdown_entry(entry: str) -> dict[str, Any]:
    lines = entry.splitlines()
    record: dict[str, Any] = {}
    if lines:
        title = lines[0].strip()
        if title.startswith("## Memory:"):
            title = title.removeprefix("## Memory:").strip()
            record["task_id"] = title

    idx = 1
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith("### "):
            break
        meta = _MD_META_RE.match(line)
        if meta:
            key = meta.group(1).strip().lower().replace(" ", "_")
            value = meta.group(2).strip()
            if key == "timestamp":
                record["timestamp"] = _timestamp_from_iso(value)
            elif key == "tags":
                record["tags"] = _parse_tags(value)
            elif key == "fingerprint":
                record["fingerprint"] = value.strip("`")
            elif key == "task":
                record["instruction"] = "" if value == "-" else value
            elif key == "memory":
                record["lesson"] = "" if value == "-" else value
                record["strategy"] = ""
            else:
                record[key] = "" if value == "-" else value
        idx += 1

    matches = list(_MD_SECTION_RE.finditer(entry))
    section_key = {
        "Instruction": "instruction",
        "Lesson": "lesson",
        "Strategy": "strategy",
        "Memory": "lesson",
        "Answer": "answer",
        "Prediction": "pred",
    }
    for pos, match in enumerate(matches):
        start = match.end()
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(entry)
        key = section_key.get(match.group(1).strip())
        if key:
            value = entry[start:end].strip()
            record[key] = "" if value == "-" else value

    record.setdefault("task_id", "unknown")
    record.setdefault("instruction", "")
    record.setdefault("outcome", "unknown")
    record.setdefault("lesson", "")
    record.setdefault("strategy", "")
    record.setdefault("tags", [])
    record.setdefault("answer", "")
    record.setdefault("pred", "")
    record.setdefault("timestamp", 0.0)
    return record


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

    def __init__(self, path: str | Path = "memory/long_term_memory.md") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, item: MemoryItem | dict[str, Any]) -> None:
        record = item.to_record() if isinstance(item, MemoryItem) else dict(item)
        record.setdefault("timestamp", time.time())
        if self.path.suffix.lower() == ".md":
            if record.get("outcome") == "success":
                return
            record = _compact_markdown_record(record)
        fingerprint = self._fingerprint(record)
        if fingerprint:
            record["fingerprint"] = fingerprint
            recent = self.read_all()[-80:]
            if any(row.get("fingerprint") == fingerprint for row in recent):
                return
        with _MEMORY_APPEND_LOCK:
            if self.path.suffix.lower() == ".md":
                self._append_markdown(record)
            else:
                self._append_jsonl(record)

    def _append_markdown(self, record: dict[str, Any]) -> None:
        if not self.path.exists() or not self.path.read_text(encoding="utf-8").strip():
            self.path.write_text(_STORE_HEADER, encoding="utf-8")
        next_index = len(self._read_markdown(self.path)) + 1
        with self.path.open("a", encoding="utf-8") as f:
            f.write(_markdown_record(record, index=next_index))
            f.write("\n")

    def _append_jsonl(self, record: dict[str, Any]) -> None:
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
        rows: list[dict[str, Any]] = []
        if self.path.exists():
            rows.extend(self._read_path(self.path))
        if self.path.suffix.lower() == ".md":
            legacy_path = self.path.with_suffix(".jsonl")
            if legacy_path.exists():
                rows.extend(
                    _compact_markdown_record(row)
                    for row in self._read_path(legacy_path)
                    if row.get("outcome") != "success"
                )
        return self._dedupe_rows(rows)

    def _read_path(self, path: Path) -> list[dict[str, Any]]:
        if path.suffix.lower() == ".md":
            return self._read_markdown(path)
        return self._read_jsonl(path)

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    @staticmethod
    def _read_markdown(path: Path) -> list[dict[str, Any]]:
        text = path.read_text(encoding="utf-8")
        matches = list(_MD_ENTRY_RE.finditer(text))
        rows: list[dict[str, Any]] = []
        for idx, match in enumerate(matches):
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            entry = text[match.start():end].strip()
            if entry:
                rows.append(_parse_markdown_entry(entry))
        return rows

    @staticmethod
    def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            key = str(row.get("fingerprint") or "")
            if not key:
                key = MemoryStore._fingerprint(row)
                if key:
                    row["fingerprint"] = key
            if not key:
                key = "|".join(str(row.get(field, "")) for field in ("task_id", "instruction"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        query_lower = (query or "").lower()
        query_family = ""
        if "2wikimultihopqa" in query_lower or "candidate context:" in query_lower:
            query_family = "multihop"
        elif "图像" in query or "image" in query_lower:
            query_family = "image"

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in self.read_all():
            haystack = " ".join(
                str(row.get(key, ""))
                for key in ("instruction", "lesson", "strategy", "tags", "answer", "pred")
            )
            overlap = len(query_tokens & _tokens(haystack))
            if overlap <= 0:
                continue
            tags = {str(x).lower() for x in row.get("tags", [])}
            family_bonus = 1.5 if query_family and query_family in tags else 0.0
            specificity_text = str(row.get("lesson", "")) + str(row.get("strategy", ""))
            specificity_bonus = min(len(_tokens(specificity_text)) / 60, 1.0)
            scored.append((overlap + family_bonus + specificity_bonus, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [row for _, row in scored[: max(0, int(k))]]


def format_memories_for_prompt(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return ""
    max_items = max(0, int(os.getenv("MEMORY_PROMPT_K", "4")))
    lines = [
        "## Compact Memory",
        "All items are failure reflections from previous wrong attempts.",
        "Reuse only the corrective tactics; do not treat them as facts for the current question.",
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
            f"- [{item['kind']}] {item['action']}"
        )
        if emitted >= max_items:
            break
    if emitted == 0:
        return ""
    return "\n".join(lines).strip()
