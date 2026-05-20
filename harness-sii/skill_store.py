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
_LONG_TERM_HEADING = "## Long-Term Memory"
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
_DISTINCTIVE_STOPWORDS = _GENERIC_TRIGGERS | _FAMILY_TAGS | {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "between",
    "both",
    "by",
    "final",
    "for",
    "from",
    "had",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "may",
    "needed",
    "of",
    "only",
    "or",
    "please",
    "problem",
    "question",
    "return",
    "specific",
    "the",
    "their",
    "this",
    "to",
    "was",
    "when",
    "with",
    "within",
    "years",
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
MAX_SKILL_BODY_CHARS = int(os.getenv("MAX_SKILL_BODY_CHARS", "4200"))
DEFAULT_SKILL_RETRIEVE_K = int(os.getenv("SKILL_RETRIEVE_K", "2"))
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


def _distinctive_overlap_bonus(skill: "Skill", query_tokens: set[str]) -> float:
    fields = " ".join([skill.skill_id, skill.title, skill.summary, " ".join(skill.triggers)])
    skill_tokens = {
        token
        for token in _tokens(fields)
        if token not in _DISTINCTIVE_STOPWORDS and len(token) >= 3
    }
    query_specific = {
        token
        for token in query_tokens
        if token not in _DISTINCTIVE_STOPWORDS and len(token) >= 3
    }
    id_tokens = {
        token
        for token in _tokens(skill.skill_id)
        if token not in _DISTINCTIVE_STOPWORDS and len(token) >= 3
    }
    overlap = query_specific & skill_tokens
    id_overlap = query_specific & id_tokens
    return min(3.5, 0.28 * len(overlap) + 0.35 * len(id_overlap))


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
    """Require skills to be durable procedures, not loose memories."""
    lowered = (body or "").lower()
    required_groups = (
        ("适用", "触发", "when to use", "use when"),
        ("诊断", "判断", "diagnose", "credit assignment"),
        ("上下文", "证据", "流程", "步骤", "procedure", "workflow"),
        ("工具", "tool", "search", "browser"),
        ("停止", "回退", "stop", "fallback"),
        ("输出", "格式", "answer contract", "output"),
    )
    return all(any(token in lowered for token in group) for group in required_groups)


def _is_actionable_body(body: str, *, is_new: bool) -> bool:
    min_chars = MIN_NEW_SKILL_BODY_CHARS if is_new else MIN_UPDATE_SKILL_BODY_CHARS
    return (
        len((body or "").strip()) >= min_chars
        and len((body or "").strip()) <= MAX_SKILL_BODY_CHARS
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


def _bounded_merge(old_body: str, new_body: str) -> str:
    merged = _merge_short_update(old_body, new_body)
    if len(merged.strip()) > MAX_SKILL_BODY_CHARS:
        return old_body
    return merged


def _memory_long_section(body: str) -> str:
    body = (body or "").strip()
    if not body:
        return (
            _LONG_TERM_HEADING
            + "\n### 适用触发 / When to use\n"
            + "- Use only when no narrower learned skill matches and the task needs general evidence/tool discipline.\n"
            + "- Prefer a knowledge or domain skill whenever one directly matches the answer type or entity class.\n\n"
            + "### 失败诊断 / Credit assignment\n"
            + "- First decide whether the risk is evidence selection, tool choice, reasoning composition, stopping, or output span.\n"
            + "- Do not promote one-off entity facts into long-term memory; keep only rules that change future context construction.\n\n"
            + "### 上下文/证据流程\n"
            + "- Identify answer type, core entity, target relation, and the one missing evidence point.\n"
            + "- Use compact evidence, source digest, candidate context, and already returned tool evidence before broad search.\n"
            + "- Treat memory as strategy only; current-task evidence always wins.\n\n"
            + "### 工具计划\n"
            + "- Call a tool only for the named evidence gap.\n"
            + "- Prefer one targeted search query; open browser only when snippets do not contain the needed relation.\n\n"
            + "### 停止/回退条件\n"
            + "- Stop once current evidence supports the exact requested span.\n"
            + "- After repeated low-signal results, change strategy or answer from best supported evidence.\n\n"
            + "### 输出格式风险\n"
            + "- Preserve requested language, unit, granularity, and wrapper.\n"
            + "- Output the answer body only inside <answer>...</answer>."
        )
    if _LONG_TERM_HEADING not in body:
        body = _LONG_TERM_HEADING + "\n" + body
    return body.strip()


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
        body = _compact(self.body, int(os.getenv("SKILL_PROMPT_CHARS", "650")))
        triggers = f"; triggers={', '.join(self.triggers[:5])}" if self.triggers else ""
        return f"### {label}: {summary.lstrip(' | ') or self.title}{triggers}\n{body}"


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
                + _distinctive_overlap_bonus(skill, query_tokens)
                + learned_bonus
                + _specificity_bonus(skill)
                + skill.confidence * 0.15
            )
            if family == "general" and skill.skill_id.startswith("benchmark-"):
                score += 0.35
            if skill.skill_id in AGGREGATE_SKILL_IDS:
                score -= 0.35
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
            if skill_id == "memory":
                body = _memory_long_section(body)
            if not body:
                continue
            if len(body.strip()) > MAX_SKILL_BODY_CHARS:
                continue
            if skill_id == "memory" and old and not _is_actionable_body(body, is_new=False):
                body = _bounded_merge(_memory_long_section(old.body), _memory_long_section(body))
            elif skill_id == "memory" and not old and not _is_actionable_body(body, is_new=True):
                body = _memory_long_section("")
            elif old:
                if not _is_actionable_body(body, is_new=False):
                    body = _bounded_merge(old.body, body)
                elif len(body) < len(old.body) * 0.45 and _actionability_score(body) <= _actionability_score(old.body):
                    body = _bounded_merge(old.body, body)
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
            "This is a compact routing index for long-term learned skills.",
            "",
            "Use it to choose which skill files are worth reading. When a skill strongly matches, lock its compact procedure into generator context.",
            "",
            "## How Curator Uses This",
            "",
            "1. Read the current question first: answer type, entities, relation, evidence already present, and the exact missing evidence.",
            "2. Use this index only for routing. Select a skill only when its summary/triggers match the question's concrete risk.",
            "3. Read at most the few selected skill bodies, digest them, then write a short problem-specific context for generator.",
            "4. The generator context should contain actions, evidence gaps, tool conditions, stop rules, answer contract, and a compact locked-skill procedure when a skill matches.",
            "5. If no skill strongly matches, use `general/memory.md` as a fallback process, not as a source of facts.",
            "",
            "## How Reflector Uses This",
            "",
            "1. Do credit assignment from the trajectory: evidence, tool, reasoning, stopping, or output-format failure.",
            "2. Update only the skill whose trigger truly matches the reusable failure mode.",
            "3. Create a new knowledge/task skill only when the pattern has a narrow stable trigger and a reusable procedure.",
            "4. Benchmark skills may keep distilled trajectory/search steps; avoid only raw task IDs, noisy logs, and unsupported one-off facts.",
            "",
            "## Memory Boundary",
            "",
            "- `general/memory.md` is the long-term fallback memory skill for durable evidence/tool/format procedure.",
            "- `_memory/short_term.md` is short-term trajectory diagnostics. It is not a skill and must not be loaded into generator context.",
            "- Current-task evidence always overrides learned memory.",
            "",
            "## Directory Routing",
            "",
            "- `simplevqa/`: visual QA, OCR, image-entity and image-to-attribute skills.",
            "- `2wiki/`: 2WikiMultihopQA evidence-graph and comparison skills.",
            "- `general/`: cross-dataset fallback, tool, evidence, format, and other generic procedures.",
            "",
            "## Seed Skill",
            "",
            "- `init_skill`: seed startup guidance in `../skills/init_skill.md`; use only when no learned skill clearly applies.",
            "",
            "## Learned Skill Catalog",
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
        for value in (update.get("title"), update.get("summary")):
            candidate = _slug(str(value or ""))
            if candidate and candidate not in _GENERIC_TRIGGERS and candidate not in _FAMILY_TAGS:
                return candidate
        return "memory"

    def _canonical_skill_id(self, skill_id: str, update: dict[str, Any]) -> str:
        raw = str(skill_id or "").strip().lower()
        if raw in AGGREGATE_SKILL_IDS or raw == "init_skill":
            return raw
        if raw:
            first = raw.split(".", 1)[0]
            if first in AGGREGATE_SKILL_IDS:
                return first
            candidate = _slug(raw)
            if candidate and candidate not in _GENERIC_TRIGGERS and candidate not in _FAMILY_TAGS:
                return candidate
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
        "## Selected Micro-Skills",
        "Use only if the trigger matches; current evidence wins.",
    ]
    for skill in skills:
        lines.append(skill.to_prompt_block())
    return "\n".join(lines).strip()
