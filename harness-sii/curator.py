"""Curator-agent context assembly.

The curator is responsible for deciding what the answering agent should see:
task profile, tool policy, and a compact set of skills.  This replaces the old
memory prompt injection with a single skill-centric context path.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from memory_store import MemoryStore
from skill_store import Skill, SkillStore, infer_task_family

CURATOR_CONTEXT_MAX_CHARS = int(os.getenv("CURATOR_CONTEXT_MAX_CHARS", "700"))
CURATOR_CONTEXT_ITEM_CHARS = int(os.getenv("CURATOR_CONTEXT_ITEM_CHARS", "90"))
CURATOR_PROBLEM_CHARS = int(os.getenv("CURATOR_PROBLEM_CHARS", "260"))


@dataclass
class CuratedContext:
    system_prompt: str
    family: str
    selected_skills: list[Skill]
    profile: dict[str, Any]


class CuratorAgent:
    """LLM curator that writes the generator context and selects skill files."""

    def __init__(self, skill_store: SkillStore, memory_store: MemoryStore | None = None) -> None:
        self.skill_store = skill_store
        self.memory_store = memory_store

    def curate(
        self,
        *,
        task: dict[str, Any],
        base_system_prompt: str,
        tools_schema: list[dict[str, Any]] | None = None,
        evolved: bool = True,
        client: Any | None = None,
        model_name: str | None = None,
    ) -> CuratedContext:
        instruction = str(task.get("instruction") or "")
        if not evolved:
            return CuratedContext(
                system_prompt=base_system_prompt,
                family=infer_task_family(instruction),
                selected_skills=[],
                profile={"mode": "baseline"},
            )

        profile = self._profile_task(task, tools_schema or [])
        curator_plan = self._llm_curate(
            task=task,
            profile=profile,
            tools_schema=tools_schema or [],
            client=client,
            model_name=model_name,
        )
        if curator_plan:
            skills = self._skills_from_plan(curator_plan, task, profile)
            context = self._context_from_plan(curator_plan, task, profile, skills, tools_schema or [])
            profile = {**profile, "curator_source": "llm", "curator_plan": curator_plan}
        else:
            skills = self._fallback_skills(task, profile)
            context = self._fallback_context_block(task, profile, skills, tools_schema or [])
            profile = {**profile, "curator_source": "fallback"}
        profile = {
            **profile,
            "short_term_memory_candidates": 0,
            "short_term_memory_count": 0,
            "long_term_skill_count": len(skills),
        }
        return CuratedContext(
            system_prompt=f"{base_system_prompt}\n\n{context}".strip(),
            family=profile["family"],
            selected_skills=skills,
            profile=profile,
        )

    def _routing_text(self, task: dict[str, Any], profile: dict[str, Any]) -> str:
        parts = [
            str(task.get("instruction") or ""),
            str(task.get("image_url") or ""),
            str(task.get("image_path") or ""),
            " ".join(profile.get("needs", [])),
            profile.get("family", ""),
        ]
        return "\n".join(part for part in parts if part)

    def _fallback_skills(self, task: dict[str, Any], profile: dict[str, Any]) -> list[Skill]:
        return self.skill_store.retrieve(
            self._routing_text(task, profile),
            family=profile["family"],
            k=int(os.getenv("SKILL_RETRIEVE_K", "3")),
        )

    def _profile_task(self, task: dict[str, Any], tools_schema: list[dict[str, Any]]) -> dict[str, Any]:
        instruction = str(task.get("instruction") or "")
        lowered = instruction.lower()
        family = infer_task_family(
            "\n".join(
                str(x or "")
                for x in (
                    instruction,
                    task.get("image_url"),
                    task.get("image_path"),
                    task.get("atomic_fact"),
                    task.get("source_digest"),
                )
            )
        )
        needs: list[str] = []
        evidence_inputs: list[str] = []
        answer_contract: list[str] = []
        if task.get("image_b64") or task.get("image_url") or task.get("image_path") or "image" in lowered or "图像" in instruction:
            needs.append("visual")
            evidence_inputs.append("image")
        if any(x in lowered for x in ("wiki", "multihop", "candidate context", "2wiki")) or "多跳" in instruction:
            needs.append("multihop")
            evidence_inputs.append("candidate-context")
        if any(x in instruction for x in ("搜索", "查询", "网页", "官网")) or any(x in lowered for x in ("search", "web", "current", "latest")):
            needs.append("search")
        if any(x in instruction for x in ("最终答案", "只输出", "格式")) or "<answer>" in lowered:
            needs.append("format")
            answer_contract.append("strict-format")
        if any(x in lowered for x in ("atomic_fact", "source_digest", "context packet", "candidate context")):
            evidence_inputs.append("compact-evidence")
        if any(x in instruction for x in ("多少", "几", "第几", "哪一年", "日期", "时间")):
            answer_contract.append("granularity-sensitive")
        available_tools = [
            str((tool.get("function") or {}).get("name"))
            for tool in tools_schema
            if isinstance(tool, dict) and tool.get("function")
        ]
        return {
            "family": family,
            "needs": needs or ["reasoning"],
            "evidence_inputs": evidence_inputs or ["question-only"],
            "answer_contract": answer_contract or ["concise-span"],
            "available_tools": available_tools,
            "has_gold": bool(str(task.get("answer") or "").strip()),
        }

    def _llm_curate(
        self,
        *,
        task: dict[str, Any],
        profile: dict[str, Any],
        tools_schema: list[dict[str, Any]],
        client: Any | None,
        model_name: str | None,
    ) -> dict[str, Any] | None:
        if client is None or not model_name or os.getenv("DISABLE_CURATOR_LLM", "0") == "1":
            return None

        candidate_skills = self.skill_store.retrieve(
            self._routing_text(task, profile),
            family=profile["family"],
            k=int(os.getenv("CURATOR_SKILL_CONTEXT_K", "3")),
        )
        available_skills = [
            {
                "skill_id": skill.skill_id,
                "title": skill.title,
                "domains": skill.domains,
                "triggers": skill.triggers[:12],
                "summary": skill.summary,
            }
            for skill in self.skill_store.all_skills()
        ]
        skill_context = [
            {
                "skill_id": skill.skill_id,
                "title": skill.title,
                "domains": skill.domains,
                "triggers": skill.triggers[:12],
                "summary": skill.summary,
                "body_excerpt": str(skill.body or "")[: int(os.getenv("CURATOR_SKILL_BODY_CHARS", "900"))],
            }
            for skill in candidate_skills
        ]
        tool_names = [
            str((tool.get("function") or {}).get("name"))
            for tool in tools_schema
            if isinstance(tool, dict) and tool.get("function")
        ]
        user_payload = {
            "problem": task.get("instruction", ""),
            "has_image": bool(task.get("image_b64") or task.get("image_url") or task.get("image_path")),
            "image_url": task.get("image_url", ""),
            "image_path": task.get("image_path", ""),
            "profile_hint": profile,
            "available_tools": tool_names,
            "long_term_skill_index": self.skill_store.manifest_text(),
            "available_skills": available_skills,
            "candidate_skill_context": skill_context,
        }
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": CURATOR_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False),
                    },
                ],
                temperature=0.2,
                max_tokens=int(os.getenv("CURATOR_MAX_TOKENS", "900")),
                extra_body={"enable_thinking": False},
            )
            return _json_from_text(resp.choices[0].message.content or "")
        except Exception:
            return None

    def _skills_from_plan(
        self,
        curator_plan: dict[str, Any],
        task: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[Skill]:
        selected: list[Skill] = []
        seen: set[str] = set()
        fallback_ranked = self._fallback_skills(task, profile)
        max_skills = int(os.getenv("CURATOR_MAX_SELECTED_SKILLS", "2"))
        for skill_id in curator_plan.get("selected_skill_ids", []) or []:
            skill = self.skill_store.get(str(skill_id))
            if not skill or skill.skill_id in seen:
                continue
            if skill.skill_id in {"memory", "init_skill"} and selected:
                continue
            if skill:
                selected.append(skill)
                seen.add(skill.skill_id)
            if len(selected) >= max_skills:
                break

        min_k = int(os.getenv("CURATOR_FALLBACK_SKILL_MIN", "0"))
        if len(selected) < min_k:
            for skill in fallback_ranked:
                if skill.skill_id not in seen:
                    selected.append(skill)
                    seen.add(skill.skill_id)
                if len(selected) >= max_skills:
                    break
        if not selected and os.getenv("CURATOR_USE_FALLBACK_SKILLS", "1") == "1":
            for skill in fallback_ranked:
                if skill.skill_id in {"memory", "init_skill"} and fallback_ranked[:1] != [skill]:
                    continue
                selected.append(skill)
                if len(selected) >= max_skills:
                    break
        return selected[:max_skills]

    def _context_from_plan(
        self,
        curator_plan: dict[str, Any],
        task: dict[str, Any],
        profile: dict[str, Any],
        skills: list[Skill],
        tools_schema: list[dict[str, Any]],
    ) -> str:
        reqs = _as_lines(curator_plan.get("task_requirements"), max_items=1)
        points = _as_lines(curator_plan.get("answering_points"), max_items=2)
        evidence_plan = _as_lines(curator_plan.get("evidence_plan"), max_items=2)
        tool_plan = _as_lines(curator_plan.get("tool_plan"), max_items=2)
        stop_conditions = _as_lines(curator_plan.get("stop_conditions"), max_items=1)
        answer_contract = _as_lines(curator_plan.get("answer_contract"), max_items=1)
        cautions = _as_lines(curator_plan.get("cautions"), max_items=1)

        lines = [
            "## ReAct Context",
            "",
            "### Q",
            _clip(str(task.get("instruction") or "").strip(), CURATOR_PROBLEM_CHARS),
            "",
            "### Goal",
            *(reqs or ["- Solve the user problem and output only the requested final answer."]),
            "",
            "### Focus",
            *(points or ["- Identify the core entity/relation, gather only missing evidence, then answer concisely."]),
            "",
            "### Evidence",
            *(evidence_plan or ["- Use provided compact evidence first; call tools only for an explicit unresolved evidence gap."]),
        ]

        if tool_plan:
            lines.extend(["", "### Tools", *tool_plan])
        else:
            lines.extend(["", "### Tools", "- Use tools only for a concrete missing fact."])

        lines.extend(
            [
                "",
                "### Stop",
                *(stop_conditions or ["- Stop tool use when the exact requested answer span is supported by current evidence.", "- After two low-signal tool results, switch strategy or answer from best evidence."]),
                "",
                "### Output",
                *(answer_contract or ["- Final output must be exactly one concise answer inside <answer>...</answer>."]),
            ]
        )

        if cautions:
            lines.extend(["", "### Watch", *cautions])
        return _cap_context(lines, CURATOR_CONTEXT_MAX_CHARS)

    def _fallback_context_block(
        self,
        task: dict[str, Any],
        profile: dict[str, Any],
        skills: list[Skill],
        tools_schema: list[dict[str, Any]],
    ) -> str:
        domain_points = self._fallback_domain_points(task, profile)
        answering_points = _clip_items(domain_points["answering_points"], 1)
        evidence_plan = _clip_items(domain_points["evidence_plan"], 1)
        tool_plan = _clip_items(domain_points["tool_plan"], 1)
        stop_conditions = _clip_items(domain_points["stop_conditions"], 1)
        answer_contract = _clip_items(domain_points["answer_contract"], 1)
        lines = [
            "## ReAct Context",
            "",
            "### Q",
            _clip(str(task.get("instruction") or "").strip(), CURATOR_PROBLEM_CHARS),
            "",
            "### Goal",
            "- Identify the requested answer type and exact granularity.",
        ]

        lines.extend(
            [
                "",
                "### Focus",
                "- Identify entity, relation, and missing evidence.",
                *answering_points,
                "",
                "### Evidence",
                "- Use current hints/tool evidence before search.",
                *evidence_plan,
            ]
        )

        tool_names = profile.get("available_tools") or []
        if tool_names:
            lines.extend(
                [
                    "",
                    "### Tools",
                    "- available: " + _clip(", ".join(tool_names), 160),
                    "- Tool only for the named evidence gap.",
                    *tool_plan,
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "### Tools",
                    "- No external tools are registered; answer only from current evidence.",
                ]
            )

        lines.extend(
            [
                "",
                "### Stop",
                "- Stop when exact answer span is supported.",
                *stop_conditions,
                "",
                "### Output",
                "- Put only the answer body in <answer>.",
                *answer_contract,
            ]
        )
        return _cap_context(lines, CURATOR_CONTEXT_MAX_CHARS)

    def _fallback_domain_points(self, task: dict[str, Any], profile: dict[str, Any]) -> dict[str, list[str]]:
        instruction = str(task.get("instruction") or "")
        lowered = instruction.lower()
        points: dict[str, list[str]] = {
            "answering_points": [],
            "evidence_plan": [],
            "tool_plan": [],
            "stop_conditions": [],
            "answer_contract": [],
        }
        if profile.get("family") == "simplevqa":
            points["answering_points"].extend(
                [
                    "- SimpleVQA: decide visible answer vs entity-to-attribute bridge.",
                    "- If atomic_fact names the entity, bridge from it to the asked attribute.",
                ]
            )
            points["evidence_plan"].extend(
                [
                    "- Prefer visible/OCR evidence, then atomic_fact/source_digest, then targeted search.",
                    "- Avoid image-search loops without a usable http(s) image URL.",
                ]
            )
            points["stop_conditions"].append(
                "- Stop once the visible span or bridged attribute matches the question."
            )
        if any(x in lowered for x in ("atomic_fact", "source_digest", "原子事实", "识别线索")):
            points["evidence_plan"].append(
                "- Use atomic/source hints for routing; answer the original relation."
            )
        if profile.get("family") == "2wiki":
            points["answering_points"].extend(
                [
                    "- 2Wiki: classify chain, comparison, bridge comparison, or same-country check.",
                    "- Use triples as the graph; sentences only disambiguate names/dates/aliases.",
                ]
            )
            points["evidence_plan"].extend(
                [
                    "- Evidence order: triples, supporting sentences, candidate context if ambiguous.",
                    "- Chain: subject -> bridge -> answer; return the final object.",
                    "- Comparison: normalize dates/numbers/countries before deciding.",
                ]
            )
            points["stop_conditions"].append(
                "- Stop when the graph/comparison yields one supported span."
            )
            points["answer_contract"].append(
                "- For yes/no 2Wiki, answer exactly yes or no."
            )
        if any(x in lowered for x in ("表格", "图表", "公式", "equation", "table", "chart", "price", "average", "total")):
            points["answering_points"].append(
                "- Preserve row/column/axis/unit before computing."
            )
            points["answer_contract"].append(
                "- Preserve requested units, decimals, and order."
            )
        if any(x in instruction for x in ("多少", "几个", "几次")) or any(x in lowered for x in ("how many", "count")):
            points["answering_points"].append(
                "- For counts, fix inclusion scope before answering."
            )
            points["answer_contract"].append("- Prefer the shortest numeric answer unless the question explicitly asks for a unit.")
        if any(x in instruction for x in ("左", "右", "前", "后", "上", "下")) or any(x in lowered for x in ("left", "right", "front", "behind")):
            points["answering_points"].append(
                "- Use viewer perspective unless object-intrinsic direction is requested."
            )
        if "search" in profile.get("needs", []):
            points["tool_plan"].append(
                "- Query exact entity/bridge plus missing attribute."
            )
        return points

CURATOR_SYSTEM_PROMPT = """你是 curator-agent，负责把“当前题目 + 可用工具 + 长期 skill 知识”压缩成 generator 的专用作战上下文。

你的输出不是通用提示词，也不是 skill 摘抄；它必须是当前题专属的 ReAct 战术卡片。

内部工作流：
1. 题目诊断：判断答案类型、要求粒度、语言/单位/包装，以及题目属于图像、搜索、2Wiki、多跳、格式控制还是纯推理。
2. 证据盘点：指出当前题已有证据（如 atomic_fact、source_digest、candidate context、image/text clues、tool evidence）能解决什么，还缺什么。
3. skill 消化：阅读 candidate_skill_context，只吸收真正匹配当前题的策略或知识型流程；把它改写成当前题具体动作，不得复制 skill 原文。
4. 工具计划：只有存在明确证据缺口时才设计工具调用；写出查询/浏览目标和停止条件。
5. 上下文裁剪：删掉背景解释、泛泛原则、skill 名称说明、系统提示和 short-term memory。

质量要求：
- 每条都必须包含当前题的实体、关系、证据缺口、工具条件或输出约束之一；禁止“仔细分析”“使用相关证据”这类空话。
- 当前题证据优先；skill 只能提供策略和领域流程，不能替代当前证据。
- 如果某个 skill 强匹配，selected_skill_ids 填它，并把其有效内容转写到 evidence/tool/stop/output 中。
- 为小模型服务：每个字段普通题 0-1 条，复杂题最多 2 条；每条尽量 25 个汉字或 20 个英文词以内。
- 契合 ReAct：优先写“要看什么证据、何时用工具、何时停止、答案怎么包”，不要写背景解释。
- 不要给最终答案，不要泄露 gold answer，不要输出 short-term memory 字段。

只输出 JSON，字段固定如下：
{
  "task_requirements": ["说明本题到底要什么答案，包括粒度/语言/单位/包装"],
  "answering_points": ["当前题要抓的实体、关系、桥接点或比较维度"],
  "evidence_plan": ["已有证据如何用；还缺哪一个具体证据才需要工具"],
  "tool_plan": ["仅在证据缺口存在时调用什么工具、用什么查询/目标"],
  "stop_conditions": ["什么证据出现就停止；低信号时如何回退"],
  "answer_contract": ["最终 <answer> 内应放什么、不应放什么"],
  "selected_skill_ids": ["只列强匹配 skill_id；无则空数组"],
  "cautions": ["当前题最容易错的具体点"]
}
"""


def _json_from_text(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _clip(text: str, max_chars: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "…"


def _as_lines(value: Any, *, max_items: int = 2, max_chars: int | None = None) -> list[str]:
    if isinstance(value, list):
        items = [str(x).strip() for x in value if str(x).strip()]
    else:
        items = [str(value).strip()] if str(value or "").strip() else []
    max_chars = CURATOR_CONTEXT_ITEM_CHARS if max_chars is None else max_chars
    lines: list[str] = []
    for item in items[:max_items]:
        item = _clip(item.removeprefix("-").strip(), max_chars)
        if item:
            lines.append(f"- {item}")
    return lines


def _clip_items(items: list[str], max_items: int) -> list[str]:
    return [f"- {_clip(str(item).removeprefix('-').strip(), CURATOR_CONTEXT_ITEM_CHARS)}" for item in items[:max_items] if str(item).strip()]


def _cap_context(lines: list[str], max_chars: int) -> str:
    text = "\n".join(lines).strip()
    if len(text) <= max_chars:
        return text
    keep_sections = {"## ReAct Context", "### Q", "### Goal", "### Focus", "### Evidence", "### Tools", "### Stop", "### Output"}
    compact: list[str] = []
    current_heading = ""
    for line in lines:
        if line.startswith("#"):
            current_heading = line
            if line in keep_sections:
                compact.append(line)
            continue
        if current_heading not in keep_sections:
            continue
        if not line.strip():
            if compact and compact[-1] != "":
                compact.append("")
            continue
        if line.startswith("-"):
            if sum(1 for x in compact if x.startswith("-")) >= 8:
                continue
            candidate = _clip(line, CURATOR_CONTEXT_ITEM_CHARS + 2)
        else:
            candidate = _clip(line, CURATOR_PROBLEM_CHARS)
        next_text = "\n".join([*compact, candidate]).strip()
        if len(next_text) > max_chars:
            break
        compact.append(candidate)
    return "\n".join(compact).strip()
