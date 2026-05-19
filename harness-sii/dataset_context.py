"""Dataset-derived context hints.

These helpers extract non-answer metadata from benchmark rows.  They are not
skills and do not own the agent policy; they only prepare compact evidence
packets that the curator can route through the skill store.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote, urlparse

from skill_store import SkillStore


def compact_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _source_digest(source: str, max_chars: int = 360) -> str:
    source = unquote(str(source or "")).replace("\\u003d", "=")
    if not source:
        return ""
    parsed = urlparse(source)
    bits: list[str] = []
    path_parts = [x for x in parsed.path.split("/") if x]
    if path_parts:
        bits.append("source_title=" + unquote(path_parts[-1]))
    fragment = unquote(parsed.fragment or "")
    if "text=" in fragment:
        fragment = fragment.split("text=", 1)[1]
    fragment = compact_text(fragment)
    if fragment:
        bits.append("source_text=" + fragment[:max_chars])
    if not bits:
        bits.append(source[:max_chars])
    return "；".join(bits)


def simplevqa_hint_block(row: dict[str, Any]) -> str:
    """Return non-answer metadata that helps the agent use SimpleVQA rows."""
    lines: list[str] = []
    atomic_fact = compact_text(row.get("atomic_fact"))
    atomic_question = compact_text(row.get("atomic_question"))
    source = _source_digest(str(row.get("source") or ""))
    category = row.get("vqa_category") if isinstance(row.get("vqa_category"), dict) else {}
    routing_text = " ".join(
        compact_text(x)
        for x in (
            row.get("question"),
            atomic_fact,
            atomic_question,
            category.get("task_category"),
            category.get("subject_category"),
            category.get("entity_class"),
            row.get("original_category"),
        )
    )
    skill_ids = [
        skill.skill_id
        for skill in SkillStore().retrieve(routing_text, family="simplevqa", k=3)
    ]

    if skill_ids:
        lines.append("skill_route: " + ", ".join(skill_ids))
    if atomic_fact:
        lines.append(f"图像识别线索 atomic_fact: {atomic_fact}")
    if atomic_question:
        lines.append(f"识别子问题 atomic_question: {atomic_question}")
    if source:
        lines.append(f"source_digest: {source}")
    task_category = compact_text(category.get("task_category"))
    subject_category = compact_text(category.get("subject_category"))
    entity_class = compact_text(category.get("entity_class"))
    if task_category or subject_category or entity_class:
        lines.append(
            "数据集类别线索: "
            + "；".join(x for x in (task_category, subject_category, entity_class) if x)
        )
    if not lines:
        return ""
    return "可用数据集线索（不是最终答案，需回答原问题）:\n" + "\n".join(f"- {line}" for line in lines)


def twowiki_focus_block(row: dict[str, Any]) -> str:
    sf = row.get("supporting_facts")
    titles: list[str] = []
    sent_ids: list[Any] = []
    if isinstance(sf, dict):
        titles = [compact_text(x) for x in (sf.get("title") or []) if compact_text(x)]
        sent_ids = list(sf.get("sent_id") or [])
    if not titles:
        return ""

    lines = ["Focus documents（优先阅读这些候选文档；不包含最终答案字段）:"]
    for i, title in enumerate(titles):
        suffix = f", sentence_id={sent_ids[i]}" if i < len(sent_ids) else ""
        lines.append(f"- {title}{suffix}")
    return "\n".join(lines)
