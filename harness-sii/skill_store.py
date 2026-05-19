"""Markdown skill storage and retrieval for the self-evolving harness.

Initial skills live in ``skills/*.md`` and are treated as the seed skillbook.
Reflector-created or reflector-updated skills are written to
``learned_skills/*.md``.  ``learned_skills/SKILL.md`` is the lightweight dynamic
index that curator and reflector read before loading concrete skill bodies.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
_SAFE_ID_RE = re.compile(r"[^0-9A-Za-z_.-]+")
_FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
_TAG_SPLIT_RE = re.compile(r"[|,，、/;；]+")
_BULLET_RE = re.compile(r"(?m)^\s*(?:[-*]|\d+[.、])\s+")
_FAMILY_TAGS = {"general", "simplevqa", "2wiki", "benchmark"}
_GENERIC_TRIGGERS = {
    "task",
    "answer",
    "tool",
    "skill",
    "reasoning",
    "evidence",
    "format",
    "search",
    "memory",
    "输出",
    "答案",
    "工具",
    "任务",
    "推理",
    "证据",
    "格式",
    "搜索",
}
AGGREGATE_SKILL_IDS = {
    "memory",
    "search",
    "browser",
    "tool",
    "format",
    "ocr",
    "image",
    "entity",
    "multihop",
    "evidence",
    "efficiency",
    "reasoning",
    "simplevqa_atomic_bridge",
    "simplevqa_cn_culture_heritage",
    "simplevqa_direct_perception",
    "simplevqa_ocr_table_chart",
    "simplevqa_landmark_entity_recognition",
    "twowiki_multihop_chain",
    "twowiki_comparison",
    "twowiki_bridge_comparison",
    "twowiki_same_country_alias",
}
MIN_NEW_SKILL_BODY_CHARS = int(os.getenv("MIN_NEW_SKILL_BODY_CHARS", "520"))
MIN_UPDATE_SKILL_BODY_CHARS = int(os.getenv("MIN_UPDATE_SKILL_BODY_CHARS", "420"))
DEFAULT_SKILL_RETRIEVE_K = int(os.getenv("SKILL_RETRIEVE_K", "3"))
SKILL_MIN_SCORE = float(os.getenv("SKILL_MIN_SCORE", "2.75"))


def infer_task_family(instruction: str) -> str:
    text = instruction or ""
    lowered = text.lower()
    if "2wikimultihopqa" in lowered or "candidate context:" in lowered or "context packet:" in lowered:
        return "2wiki"
    if any(x in text for x in ("图像", "输入图像", "图中", "图片", "照片", "图里")) or "image" in lowered or "atomic_fact" in lowered:
        return "simplevqa"
    return "general"


def _tokens(text: str) -> set[str]:
    text = text or ""
    toks = {t.lower() for t in _TOKEN_RE.findall(text) if len(t.strip()) > 1}
    return toks


def _family_compatible(skill_domains: list[str], family: str | None) -> bool:
    if not family:
        return True
    family_domains = set(skill_domains) & _FAMILY_TAGS
    return not family_domains or family in family_domains or "general" in family_domains


def _trigger_score(skill: "Skill", query_lower: str) -> float:
    score = 0.0
    for trigger in skill.triggers:
        trigger = str(trigger or "").strip().lower()
        if not trigger or trigger in _GENERIC_TRIGGERS:
            continue
        if trigger in query_lower:
            score += 3.0 if len(trigger) >= 4 else 1.5
    return score


def _domain_score(skill: "Skill", query_tokens: set[str], family: str | None) -> float:
    score = 0.0
    for domain in skill.domains:
        domain = str(domain or "").strip().lower()
        if not domain or domain in _FAMILY_TAGS:
            continue
        if domain in query_tokens:
            score += 1.25
    if family and family != "general" and family in skill.domains:
        score += 1.5
    return score


def _specificity_bonus(skill: "Skill") -> float:
    specific_triggers = [
        t
        for t in skill.triggers
        if len(str(t or "").strip()) >= 3 and str(t or "").strip().lower() not in _GENERIC_TRIGGERS
    ]
    domain_count = len(
        [
            d
            for d in skill.domains
            if str(d or "").strip().lower() not in _FAMILY_TAGS
            and str(d or "").strip().lower() not in _GENERIC_TRIGGERS
        ]
    )
    return min(1.0, 0.25 * len(specific_triggers) + 0.15 * domain_count)


def _compact(text: Any, limit: int = 240) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "..."


def _split_csv(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = _TAG_SPLIT_RE.split(str(value or ""))
    clean: list[str] = []
    for item in raw:
        text = str(item or "").strip("` ").lower()
        if text and text not in clean:
            clean.append(text)
    return clean


def _slug(value: str) -> str:
    safe = _SAFE_ID_RE.sub("-", value.strip()).strip("-._").lower()
    return safe[:96] or f"skill-{int(time.time())}"


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
    return meta, text[match.end():].strip()


def _format_list(values: list[str]) -> str:
    return ", ".join(str(x).strip() for x in values if str(x).strip())


def _dataset_group_for(skill_id: str, domains: list[str] | None = None) -> str:
    values = {str(skill_id or "").strip().lower()}
    values.update(str(x or "").strip().lower() for x in (domains or []))
    if any(x == "2wiki" or x.startswith("twowiki") for x in values):
        return "2wiki"
    if any(x == "simplevqa" or x.startswith("simplevqa") for x in values):
        return "simplevqa"
    return "general"


def _clamp_confidence(value: Any, default: float = 0.65) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return max(0.05, min(1.0, score))


def _actionability_score(body: str) -> int:
    lowered = (body or "").lower()
    markers = (
        "when",
        "use",
        "step",
        "stop",
        "fallback",
        "output",
        "evidence",
        "适用",
        "触发",
        "步骤",
        "流程",
        "停止",
        "回退",
        "输出",
        "格式",
        "证据",
        "工具",
        "检索",
        "核验",
        "条件",
    )
    return sum(1 for marker in markers if marker in lowered) + min(5, len(_BULLET_RE.findall(body or "")))


def _has_professional_skill_shape(body: str) -> bool:
    """Require skills to be procedures, not loose memories."""
    lowered = (body or "").lower()
    required_groups = (
        ("适用", "触发", "when to use", "use when"),
        ("诊断", "判断", "diagnose", "credit assignment"),
        ("流程", "步骤", "procedure", "workflow"),
        ("停止", "回退", "stop", "fallback"),
        ("输出", "格式", "answer contract", "output"),
    )
    return all(any(token in lowered for token in group) for group in required_groups)


def _is_actionable_body(body: str, *, is_new: bool) -> bool:
    min_chars = MIN_NEW_SKILL_BODY_CHARS if is_new else MIN_UPDATE_SKILL_BODY_CHARS
    return (
        len((body or "").strip()) >= min_chars
        and _actionability_score(body) >= 7
        and _has_professional_skill_shape(body)
    )


def _merge_short_update(old_body: str, new_body: str) -> str:
    new_body = re.sub(r"\s+", " ", str(new_body or "")).strip()
    if not new_body or new_body in old_body:
        return old_body
    return (
        old_body.strip()
        + "\n\n## Recent Transferable Adjustment\n"
        + "- Keep the existing procedure above as primary guidance.\n"
        + f"- Additional tactic to apply when relevant: {new_body}"
    )


@dataclass
class Skill:
    skill_id: str
    title: str
    body: str
    domains: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    summary: str = ""
    confidence: float = 0.65
    path: str = ""
    source: str = "base"

    def searchable_text(self) -> str:
        return " ".join(
            [
                self.skill_id,
                self.title,
                self.summary,
                self.body,
                " ".join(self.domains),
                " ".join(self.triggers),
            ]
        )

    def to_prompt_block(self) -> str:
        label = f"{self.skill_id}"
        summary = f" | {self.summary}" if self.summary else ""
        body = _compact(self.body, int(os.getenv("SKILL_PROMPT_CHARS", "1200")))
        domains = f"domains={', '.join(self.domains[:5])}" if self.domains else "domains=unspecified"
        triggers = f"triggers={', '.join(self.triggers[:8])}" if self.triggers else "triggers=unspecified"
        return f"### Skill: {label}\n- summary: {summary.lstrip(' | ') or self.title}\n- {domains}\n- {triggers}\n{body}"


class SkillStore:
    """Read, rank, and mutate Markdown skill files."""

    def __init__(
        self,
        path: str | Path = "skills",
        learned_path: str | Path | None = None,
    ) -> None:
        raw_path = Path(path)
        root = Path(__file__).resolve().parent
        self.path = root / raw_path if not raw_path.is_absolute() else raw_path
        learned_value = learned_path or os.getenv("LEARNED_SKILLS_DIR", "learned_skills")
        raw_learned_path = Path(learned_value)
        self.learned_path = root / raw_learned_path if not raw_learned_path.is_absolute() else raw_learned_path
        self.path.mkdir(parents=True, exist_ok=True)
        self.learned_path.mkdir(parents=True, exist_ok=True)

    def skill_files(self) -> list[Skill]:
        return self._dedupe_by_id(
            self._read_dir(self.path, source="base", recursive=False)
            + self._read_dir(self.learned_path, source="learned", recursive=True)
        )

    def _read_dir(self, directory: Path, *, source: str, recursive: bool) -> list[Skill]:
        skills: list[Skill] = []
        pattern = "**/*.md" if recursive else "*.md"
        for path in sorted(directory.glob(pattern)):
            if path.name == "SKILL.md":
                continue
            if any(part.startswith("_") for part in path.relative_to(directory).parts[:-1]):
                continue
            skill = self._read_skill_file(path, source=source)
            if skill:
                skills.append(skill)
        return skills

    @staticmethod
    def _dedupe_by_id(skills: list[Skill]) -> list[Skill]:
        by_id: dict[str, Skill] = {}
        order: list[str] = []
        for skill in skills:
            if skill.skill_id not in by_id:
                order.append(skill.skill_id)
            by_id[skill.skill_id] = skill
        return [by_id[skill_id] for skill_id in order]

    def all_skills(self) -> list[Skill]:
        return self.skill_files()

    def retrieve(self, query: str, *, family: str | None = None, k: int = DEFAULT_SKILL_RETRIEVE_K) -> list[Skill]:
        family = family or infer_task_family(query)
        query_tokens = _tokens(query)
        scored: list[tuple[float, int, Skill]] = []
        query_lower = (query or "").lower()
        init_skill: Skill | None = None
        for pos, skill in enumerate(self.all_skills()):
            if skill.skill_id == "init_skill":
                init_skill = skill
                continue
            if not _family_compatible(skill.domains, family):
                continue
            haystack = skill.searchable_text()
            overlap = len(query_tokens & _tokens(haystack))
            overlap_score = min(2.0, overlap * 0.18)
            trigger_bonus = _trigger_score(skill, query_lower)
            domain_bonus = _domain_score(skill, query_tokens, family)
            learned_bonus = 0.25 if skill.source == "learned" else 0.0
            score = (
                overlap_score
                + trigger_bonus
                + domain_bonus
                + learned_bonus
                + _specificity_bonus(skill)
                + skill.confidence * 0.15
            )
            if score >= SKILL_MIN_SCORE:
                scored.append((score, -pos, skill))
        scored.sort(reverse=True)
        selected = [skill for _, _, skill in scored[: max(0, int(k))]]
        if not selected and init_skill is not None and os.getenv("INCLUDE_INIT_SKILL_FALLBACK", "1") == "1":
            selected.append(init_skill)
        return selected

    def apply_updates(self, updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        applied: list[dict[str, Any]] = []
        for update in updates or []:
            op = str(update.get("op") or "add").lower()
            skill_id = self._canonical_skill_id(str(update.get("skill_id") or "").strip(), update)
            if not skill_id:
                skill_id = self._next_skill_id(update)
            if skill_id == "init_skill":
                continue
            if op == "delete":
                if self.delete(skill_id):
                    applied.append({"op": "delete", "skill_id": skill_id})
                continue

            old = self.get(skill_id)
            body = str(update.get("body") or update.get("content") or "").strip()
            if old and op == "update":
                body = body or old.body
            if not body:
                continue
            if old:
                if not _is_actionable_body(body, is_new=False):
                    body = _merge_short_update(old.body, body)
                elif len(body) < len(old.body) * 0.45 and _actionability_score(body) <= _actionability_score(old.body):
                    body = _merge_short_update(old.body, body)
            elif not _is_actionable_body(body, is_new=True):
                continue
            skill = Skill(
                skill_id=skill_id,
                title=str(update.get("title") or (old.title if old else skill_id)).strip(),
                body=body,
                domains=_split_csv(update.get("domains") or update.get("tags") or (old.domains if old else [])),
                triggers=_split_csv(update.get("triggers") or (old.triggers if old else [])),
                summary=str(update.get("summary") or (old.summary if old else update.get("title") or "")).strip(),
                confidence=_clamp_confidence(update.get("confidence"), old.confidence if old else 0.65),
            )
            self.upsert(skill)
            applied.append({"op": "upsert" if op in {"add", "update"} else op, "skill_id": skill.skill_id})
        if applied:
            self.refresh_manifest()
        return applied

    def upsert(self, skill: Skill) -> Path:
        skill.source = "learned"
        path = self._path_for(skill.skill_id, skill.domains)
        path.write_text(self._to_markdown(skill), encoding="utf-8")
        return path

    def delete(self, skill_id: str) -> bool:
        skill_id = self._canonical_skill_id(skill_id, {})
        if skill_id == "init_skill":
            return False
        skill = self.get(skill_id)
        if not skill:
            return False
        path = Path(skill.path)
        if path.exists() and self.learned_path.resolve() in path.resolve().parents:
            path.unlink()
            self.refresh_manifest()
            return True
        return False

    def get(self, skill_id: str) -> Skill | None:
        for skill in self.skill_files():
            if skill.skill_id == skill_id:
                return skill
        return None

    def manifest_text(self) -> str:
        manifest_path = self.learned_path / "SKILL.md"
        if manifest_path.exists():
            return manifest_path.read_text(encoding="utf-8").strip()
        return self._manifest_body(write=False).strip()

    def refresh_manifest(self) -> str:
        text = self._manifest_body(write=True)
        return text.strip()

    def _manifest_body(self, *, write: bool) -> str:
        learned = sorted(
            [skill for skill in self.skill_files() if skill.source == "learned"],
            key=lambda skill: skill.skill_id,
        )
        lines = [
            "# Learned Skill Index",
            "",
            "This file is the lightweight routing index for curator-agent and reflector-agent.",
            "",
            "Curator-agent should read this file first to decide which learned skill files may be useful, then load only the selected skill bodies.",
            "",
            "Learned skills are grouped by dataset/task family to avoid cross-dataset contamination:",
            "- `simplevqa/`: visual QA, OCR, image-entity and image-to-attribute skills.",
            "- `2wiki/`: 2WikiMultihopQA evidence-graph and comparison skills.",
            "- `general/`: cross-dataset memory and generic harness policies.",
            "- `_memory/`: short-term episodic traces; not long-term skill memory.",
            "",
            "Reflector-agent should read this file first to decide which learned skill is involved in the current failure, then update that specific skill file and refresh this index.",
            "",
            "## Seed Skill",
            "",
            "- `init_skill`: General startup guidance. Stored in `../skills/init_skill.md` and used when no learned skill clearly applies.",
            "",
            "## Learned Skills By Dataset",
            "",
        ]
        if learned:
            grouped: dict[str, list[Skill]] = {"general": [], "simplevqa": [], "2wiki": []}
            for skill in learned:
                grouped.setdefault(_dataset_group_for(skill.skill_id, skill.domains), []).append(skill)
            for group in ("general", "simplevqa", "2wiki"):
                group_skills = grouped.get(group) or []
                if not group_skills:
                    continue
                lines.extend(["", f"### {group}", ""])
                for skill in group_skills:
                    details = []
                    if skill.domains:
                        details.append("domains=" + _format_list(skill.domains[:4]))
                    specific_triggers = [
                        trigger
                        for trigger in skill.triggers
                        if str(trigger or "").strip().lower() not in _GENERIC_TRIGGERS
                    ][:5]
                    if specific_triggers:
                        details.append("triggers=" + _format_list(specific_triggers))
                    suffix = f" ({'; '.join(details)})" if details else ""
                    rel_path = Path(skill.path).resolve().relative_to(self.learned_path.resolve())
                    lines.append(f"- `{skill.skill_id}`: {skill.summary or skill.title}{suffix}; file=`{rel_path}`")
        else:
            lines.append("- No learned skills yet.")
        text = "\n".join(lines).strip() + "\n"
        if write:
            (self.learned_path / "SKILL.md").write_text(text, encoding="utf-8")
        return text

    def _path_for(self, skill_id: str, domains: list[str] | None = None) -> Path:
        group = _dataset_group_for(skill_id, domains)
        directory = self.learned_path / group
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{_slug(skill_id)}.md"

    def _next_skill_id(self, update: dict[str, Any]) -> str:
        domains = _split_csv(update.get("domains") or update.get("tags"))
        for item in domains:
            if item in AGGREGATE_SKILL_IDS and item != "memory":
                return item
        return "memory"

    def _canonical_skill_id(self, skill_id: str, update: dict[str, Any]) -> str:
        raw = str(skill_id or "").strip().lower()
        if raw in AGGREGATE_SKILL_IDS or raw == "init_skill":
            return raw
        if raw:
            first = raw.split(".", 1)[0]
            if first in AGGREGATE_SKILL_IDS:
                return first
        return ""

    def _read_skill_file(self, path: Path, *, source: str) -> Skill | None:
        try:
            meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
        except OSError:
            return None
        skill_id = meta.get("skill_id") or path.stem
        title = meta.get("title") or skill_id
        if body.startswith("# "):
            lines = body.splitlines()
            title = lines[0].removeprefix("# ").strip() or title
            body = "\n".join(lines[1:]).strip()
        return Skill(
            skill_id=skill_id,
            title=title,
            body=body,
            domains=_split_csv(meta.get("domains")),
            triggers=_split_csv(meta.get("triggers")),
            summary=meta.get("summary", ""),
            confidence=float(meta.get("confidence") or 0.65),
            path=str(path),
            source=source,
        )

    def _to_markdown(self, skill: Skill) -> str:
        meta = {
            "skill_id": skill.skill_id,
            "title": skill.title,
            "domains": _format_list(skill.domains),
            "triggers": _format_list(skill.triggers),
            "summary": skill.summary,
            "confidence": f"{skill.confidence:.2f}",
        }
        front = "\n".join(f"{key}: {value}" for key, value in meta.items())
        return f"---\n{front}\n---\n# {skill.title}\n\n{skill.body.strip()}\n"


def format_skills_for_prompt(skills: list[Skill]) -> str:
    if not skills:
        return ""
    lines = [
        "## Long-Term Skill Memory",
        "These selected learned skills are durable procedural memory. Use them for context selection, evidence handling, tool use, and answer control; they are not factual evidence for the current task.",
    ]
    for skill in skills:
        lines.append(skill.to_prompt_block())
    return "\n".join(lines).strip()
