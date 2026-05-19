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

from memory_store import MemoryStore, format_short_term_memories
from skill_store import Skill, SkillStore, format_skills_for_prompt, infer_task_family


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
        short_term_candidates = self._short_term_memories(task, profile, candidate_mode=True)
        curator_plan = self._llm_curate(
            task=task,
            profile=profile,
            tools_schema=tools_schema or [],
            short_term_candidates=short_term_candidates,
            client=client,
            model_name=model_name,
        )
        if curator_plan:
            skills = self._skills_from_plan(curator_plan, task, profile)
            short_term_memories = self._short_terms_from_plan(curator_plan, short_term_candidates, profile)
            context = self._context_from_plan(curator_plan, task, profile, skills, tools_schema or [], short_term_memories)
            profile = {**profile, "curator_source": "llm", "curator_plan": curator_plan}
        else:
            skills = self._fallback_skills(task, profile)
            short_term_memories = short_term_candidates[: self._short_term_budget(profile)]
            context = self._fallback_context_block(task, profile, skills, tools_schema or [], short_term_memories)
            profile = {**profile, "curator_source": "fallback"}
        profile = {
            **profile,
            "short_term_memory_candidates": len(short_term_candidates),
            "short_term_memory_count": len(short_term_memories),
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

    def _short_term_budget(self, profile: dict[str, Any]) -> int:
        if os.getenv("ENABLE_SHORT_TERM_MEMORY", "1") != "1":
            return 0
        max_k = int(os.getenv("SHORT_TERM_MEMORY_RETRIEVE_K", "3"))
        needs = set(profile.get("needs") or [])
        evidence = set(profile.get("evidence_inputs") or [])
        contract = set(profile.get("answer_contract") or [])
        if profile.get("family") == "general" and needs <= {"reasoning"} and evidence <= {"question-only"}:
            return 0
        if {"search", "multihop", "visual"} & needs or {"compact-evidence", "candidate-context", "image"} & evidence:
            return max(1, min(max_k, 2 + int("granularity-sensitive" in contract)))
        return min(max_k, 1)

    def _short_term_memories(self, task: dict[str, Any], profile: dict[str, Any], *, candidate_mode: bool = False):
        if self.memory_store is None:
            return []
        budget = int(os.getenv("SHORT_TERM_MEMORY_CANDIDATE_K", "8")) if candidate_mode else self._short_term_budget(profile)
        if budget <= 0:
            return []
        return self.memory_store.retrieve_short_term(
            self._routing_text(task, profile),
            family=profile["family"],
            k=budget,
        )

    def _short_terms_from_plan(
        self,
        curator_plan: dict[str, Any],
        candidates: list[Any],
        profile: dict[str, Any],
    ) -> list[Any]:
        budget = self._short_term_budget(profile)
        if budget <= 0 or not candidates:
            return []
        selected_ids = {
            str(x)
            for x in (
                curator_plan.get("selected_short_term_memory_ids")
                or curator_plan.get("selected_short_term_ids")
                or []
            )
            if str(x).strip()
        }
        if selected_ids:
            selected = [item for item in candidates if getattr(item, "memory_id", "") in selected_ids]
            return selected[:budget]
        use_short = curator_plan.get("use_short_term_memory")
        if use_short is False:
            return []
        return candidates[:budget]

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
        short_term_candidates: list[Any],
        client: Any | None,
        model_name: str | None,
    ) -> dict[str, Any] | None:
        if client is None or not model_name or os.getenv("DISABLE_CURATOR_LLM", "0") == "1":
            return None

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
            "short_term_memory_candidates": [item.to_candidate() for item in short_term_candidates],
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
                max_tokens=int(os.getenv("CURATOR_MAX_TOKENS", "2200")),
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
        max_skills = int(os.getenv("CURATOR_MAX_SELECTED_SKILLS", "3"))
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
        short_term_memories: list[Any],
    ) -> str:
        reqs = _as_lines(curator_plan.get("task_requirements"))
        points = _as_lines(curator_plan.get("answering_points"))
        evidence_plan = _as_lines(curator_plan.get("evidence_plan"))
        tool_plan = _as_lines(curator_plan.get("tool_plan"))
        stop_conditions = _as_lines(curator_plan.get("stop_conditions"))
        answer_contract = _as_lines(curator_plan.get("answer_contract"))
        cautions = _as_lines(curator_plan.get("cautions"))

        lines = [
            "## Curator-Generated Context",
            "",
            "### Problem",
            str(task.get("instruction") or "").strip(),
            "",
            "### Task Profile",
            f"- family: {profile['family']}",
            f"- needs: {', '.join(profile['needs'])}",
            f"- evidence_inputs: {', '.join(profile.get('evidence_inputs', []))}",
            f"- answer_contract: {', '.join(profile.get('answer_contract', []))}",
            f"- memory_plan: short_term={len(short_term_memories)}, long_term_skills={len(skills)}",
            "",
            "### Task Requirements",
            *(reqs or ["- Solve the user problem and output only the requested final answer."]),
            "",
            "### Answering Points",
            *(points or ["- Identify the core entity/relation, gather only missing evidence, then answer concisely."]),
            "",
            "### Evidence Plan",
            *(evidence_plan or ["- Use provided compact evidence first; call tools only for an explicit unresolved evidence gap."]),
        ]

        if tool_plan:
            lines.extend(["", "### Tool Calling Plan", *tool_plan])
        else:
            lines.extend(["", "### Tool Calling Plan", "- Use tools only when the current context is insufficient."])

        lines.extend(
            [
                "",
                "### Stop Conditions",
                *(stop_conditions or ["- Stop tool use when the exact requested answer span is supported by current evidence.", "- After two low-signal tool results, switch strategy or answer from best evidence."]),
                "",
                "### Answer Contract",
                *(answer_contract or ["- Final output must be exactly one concise answer inside <answer>...</answer>."]),
            ]
        )

        if cautions:
            lines.extend(["", "### Cautions", *cautions])

        short_term_block = format_short_term_memories(short_term_memories)
        if short_term_block:
            lines.extend(["", "### Short-Term Memory Selected By Curator", short_term_block])

        manifest = self._manifest_excerpt(skills)
        if manifest:
            lines.extend(["", "### Long-Term Skill Memory Index Selected By Curator", manifest])

        skill_block = format_skills_for_prompt(skills)
        if skill_block:
            lines.extend(["", skill_block])

        lines.extend(
            [
                "",
                "### Hidden-Context Boundary",
                "- Short-term memory is only recent trace evidence about process risks; long-term skill memory is procedural guidance.",
                "- Current-task evidence overrides both memory layers.",
                "- Do not mention curator analysis, skill names, or hidden context in the final answer.",
            ]
        )
        return "\n".join(lines).strip()

    def _fallback_context_block(
        self,
        task: dict[str, Any],
        profile: dict[str, Any],
        skills: list[Skill],
        tools_schema: list[dict[str, Any]],
        short_term_memories: list[Any],
    ) -> str:
        domain_points = self._fallback_domain_points(task, profile)
        lines = [
            "## Curator Context",
            "",
            "### Problem",
            str(task.get("instruction") or "").strip(),
            "",
            "### Task Profile",
            f"- family: {profile['family']}",
            f"- needs: {', '.join(profile['needs'])}",
            f"- evidence_inputs: {', '.join(profile.get('evidence_inputs', []))}",
            f"- answer_contract: {', '.join(profile.get('answer_contract', []))}",
            f"- memory_plan: short_term={len(short_term_memories)}, long_term_skills={len(skills)}",
            f"- has_gold_for_reflection: {str(profile['has_gold']).lower()}",
        ]
        if task.get("image_url"):
            lines.append("- image_input: online URL is available; image search may be useful if visual recognition is uncertain.")
        elif task.get("image_path"):
            lines.append("- image_input: local image path is available; avoid repeated image search if upload fails.")

        lines.extend(
            [
                "",
                "### Answering Points",
                "- Identify the requested answer type and granularity before using tools.",
                "- Extract the core entity, relation, and exact evidence gap; do not widen to nearby entities or broader attributes.",
                *domain_points["answering_points"],
                "",
                "### Evidence Plan",
                "- Use provided atomic facts, source digests, focus documents, candidate context, and returned tool evidence before broad search.",
                "- Treat learned skills as procedures, not factual evidence; verify all factual claims against current-task evidence.",
                *domain_points["evidence_plan"],
            ]
        )

        tool_names = profile.get("available_tools") or []
        if tool_names:
            lines.extend(
                [
                    "",
                    "### Tool Plan",
                    "- available: " + ", ".join(tool_names),
                    "- policy: name the missing evidence before each tool call; prefer compact search evidence; use browser only when search snippets/content are insufficient.",
                    "- stop_rule: after two low-signal tool results, switch strategy or answer from best evidence.",
                    *domain_points["tool_plan"],
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "### Tool Plan",
                    "- No external tools are registered for this run; solve from the image, user prompt, dataset hints, selected memory procedures, and current evidence only.",
                    "- Do not invent external facts when the requested answer is not visible or not supported by provided context.",
                ]
            )

        lines.extend(
            [
                "",
                "### Stop Conditions",
                "- Stop tool use when current evidence supports the exact requested answer span.",
                "- Stop after two low-signal or repeated tool results and change strategy or answer from the best supported evidence.",
                *domain_points["stop_conditions"],
                "",
                "### Answer Contract",
                "- Final output must be exactly one concise answer inside <answer>...</answer> unless the user explicitly asks otherwise.",
                "- Inside <answer>, include only the answer body: no explanation, citations, Markdown, or internal-context references.",
                *domain_points["answer_contract"],
            ]
        )

        short_term_block = format_short_term_memories(short_term_memories)
        if short_term_block:
            lines.extend(["", "### Short-Term Memory Selected By Curator", short_term_block])

        manifest = self._manifest_excerpt(skills)
        if manifest:
            lines.extend(["", "### Long-Term Skill Memory Index Selected By Curator", manifest])

        skill_block = format_skills_for_prompt(skills)
        if skill_block:
            lines.append("")
            lines.append(skill_block)

        lines.extend(
            [
                "",
                "## Answering Contract",
                "- The answering agent solves the task; the curator context only selects useful skills.",
                "- Short-term memory is recent process evidence only; long-term skill memory is durable procedure only.",
                "- Current-task evidence overrides both memory layers.",
                "- Do not mention curator analysis, skill names, hidden context, or trajectory in the final answer.",
            ]
        )
        return "\n".join(lines).strip()

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
                    "- For SimpleVQA, first classify the task as direct perception, OCR/table/chart reasoning, entity recognition, or atomic-fact bridge lookup.",
                    "- If the question asks a visible count/color/position/text span, answer from image evidence; if it asks an external attribute of a recognized entity, use the entity as a bridge.",
                ]
            )
            points["evidence_plan"].extend(
                [
                    "- Evidence priority: visible image content and OCR text first; then atomic_fact/source_digest if present; then targeted search only for missing external attributes.",
                    "- Local image_path does not by itself justify image search; avoid search_image loops unless a usable http(s) image URL exists.",
                ]
            )
            points["stop_conditions"].append(
                "- Stop once the visible span or bridge-derived attribute matches the requested answer type."
            )
        if any(x in lowered for x in ("atomic_fact", "source_digest", "原子事实", "识别线索")):
            points["evidence_plan"].append(
                "- Treat provided atomic/source hints as current-task evidence for routing, but still answer the user's original relation rather than the hint itself."
            )
        if profile.get("family") == "2wiki":
            points["answering_points"].extend(
                [
                    "- For 2Wiki, first read the question type and skill route hint, then decide whether this is a compositional chain, direct comparison, bridge comparison, or same-country/nationality check.",
                    "- Use evidence triples as the primary reasoning graph; supporting sentences are only for disambiguating names, dates, and aliases.",
                ]
            )
            points["evidence_plan"].extend(
                [
                    "- Evidence priority: evidence triples first, then supporting sentences, then candidate context only if a triple is missing or ambiguous.",
                    "- For compositional questions, follow subject --relation--> bridge --relation--> answer and return the final object.",
                    "- For comparisons, normalize dates/numbers/countries before deciding; do not compare raw strings.",
                ]
            )
            points["stop_conditions"].append(
                "- Stop once the graph path or comparison operation yields one exact answer span supported by the packet."
            )
            points["answer_contract"].append(
                "- For yes/no 2Wiki questions, answer exactly yes or no unless the prompt asks for an entity."
            )
        if any(x in lowered for x in ("表格", "图表", "公式", "equation", "table", "chart", "price", "average", "total")):
            points["answering_points"].append(
                "- Preserve row/column/axis/unit structure before computing; avoid doing arithmetic from a lossy text summary."
            )
            points["answer_contract"].append(
                "- For numeric/table answers, preserve requested units, decimals, percentages, or multiple values in the order asked."
            )
        if any(x in instruction for x in ("多少", "几个", "几次")) or any(x in lowered for x in ("how many", "count")):
            points["answering_points"].append(
                "- For counts, define the inclusion scope before answering: visible objects, letters, digits, people, categories, or items in a specific panel."
            )
            points["answer_contract"].append("- Prefer the shortest numeric answer unless the question explicitly asks for a unit.")
        if any(x in instruction for x in ("左", "右", "前", "后", "上", "下")) or any(x in lowered for x in ("left", "right", "front", "behind")):
            points["answering_points"].append(
                "- For spatial answers, use viewer perspective unless the prompt explicitly asks for the object's intrinsic left/right."
            )
        if "search" in profile.get("needs", []):
            points["tool_plan"].append(
                "- Search query should combine the exact entity/bridge clue with the missing attribute; do not search the entire prompt verbatim."
            )
        return points

    def _manifest_excerpt(self, skills: list[Skill]) -> str:
        selected = {skill.skill_id for skill in skills}
        if not selected:
            return ""
        lines: list[str] = []
        for line in self.skill_store.manifest_text().splitlines():
            stripped = line.strip()
            if any(f"`{skill_id}`" in stripped or stripped.startswith(f"- {skill_id}:") for skill_id in selected):
                lines.append(stripped)
        return "\n".join(lines[: int(os.getenv("SKILL_MANIFEST_K", "8"))])


CURATOR_SYSTEM_PROMPT = """你是 curator-agent：一个独立的大模型上下文工程师。

你的唯一任务是为后续 generator-agent 编写“解题上下文”。你不直接解题，不输出最终答案，不替 generator 调用工具。你要读懂题目、可用工具、Long-Term Skill Memory 动态索引、Short-Term Episodic Memory 候选和可选 skill 摘要，然后判断 generator 最可能需要哪些记忆层，并生成清晰、短、可执行的 context。

你的上下文工程原则来自 Meta Context Engineering / Meta-Harness：
- context 是一个可执行工件，目标是决定“存什么、检索什么、呈现什么、何时停止”，而不是复述题面。
- 不要把所有材料一次性塞给 generator；要根据题目风险自适应选择证据、工具和 skill。
- 压缩时不能丢掉会影响下游动作的诊断信息：实体、关系、答案粒度、证据缺口、工具升级条件、停止条件。
- skill 是模块化过程，不是事实来源；只有 trigger/summary 与当前题的风险明确匹配时才加载。
- 你的输出要帮助 generator 做 credit assignment：如果它失败，轨迹中应能看出是证据、工具、推理还是格式环节出了问题。
- 记忆分两层使用：Short-Term Episodic Memory 只作为近期轨迹诊断和路由线索；Long-Term Skill Memory 才是稳定可复用过程。短期记忆不能覆盖当前证据，长期 skill 不能记录一次性事实。

## 工作边界
1. 你是 context writer，不是 answerer。不要给出未经题目证据支持的最终事实答案。
2. 你可以说明“应核验什么”“应提取什么属性”“应使用什么工具”，但不要把标准答案、gold answer 或评测字段当作 generator 可见事实。
3. Long-Term Skill Memory 是 skill 路由索引，用来快速锁定可能相关的 skill 文件；不要把所有 skill 都塞给 generator。
4. Short-Term Episodic Memory 是近期轨迹候选，只能选取能提示当前题失败模式的少数条目；不要把短期轨迹里的答案、实体或具体事实当作当前题证据。
5. skills 是专业化解题策略，不是常驻提示词。选择 skill 时宁缺毋滥：简单题可以选择 0 个；普通题选择 1-2 个；只有确实跨图像/搜索/多跳/格式等多个风险时才选择 3 个。不要超过 3 个。
6. 只有当题目触发词、答案类型、工具风险或数据集线索与 skill 的 triggers/summary 明确匹配时，才选择该 skill。不要因为 skill 看起来“可能有帮助”就选择。
7. learned memory / init_skill 只能作为没有任何专业 skill 命中时的兜底经验，不可和多个专业 skill 一起塞给 generator，也不可当作当前题事实。
8. 如果题目自带 compact evidence / atomic_fact / source_digest / evidence triples，优先让 generator 使用这些证据，减少搜索。
9. 如果题目需要外部事实核验，设计最小工具计划：先 search_text，搜索证据不足再 browser；图像题只有 http(s) 图片 URL 时才建议 search_image。
10. 如果题目是 2Wiki / candidate context / focus documents，先说明桥接实体、目标关系和支持文档阅读顺序；不要默认联网搜索。
11. 如果题目是图像任务且提供 atomic_fact/source_digest，先把这些作为视觉替代证据；只有可用 http(s) image_url 且视觉识别仍不确定时才建议 search_image。
12. 如果短期记忆与当前题证据冲突，必须以当前题证据为准；短期记忆只提示“可能的失败模式/工具风险/格式风险”。

## 你要生成的 context 应包含
- task_requirements: generator 到底要回答什么，包括答案粒度、语言、单位、格式。
- answering_points: generator 解题时应抓住的核心实体、关系、证据缺口、推理顺序。
- evidence_plan: 现有证据应如何使用、缺什么证据、如何判断证据足够。
- tool_plan: 何时调用哪些工具、查询应如何构造、何时从 search 升级到 browser 或换策略。
- stop_conditions: 明确停止工具调用/停止推理的条件，避免循环和上下文膨胀。
- answer_contract: 最终答案的 span、单位、语言、标签包装、禁止解释等约束。
- selected_skill_ids: 从 available_skills 中选择要拼接正文的 skill_id；若没有强匹配，输出空数组。
- use_short_term_memory: 是否使用短期轨迹记忆。只有当近期轨迹能提示明确失败模式时才为 true。
- selected_short_term_memory_ids: 从 short_term_memory_candidates 中选择要拼接的 memory_id；若没有强匹配，输出空数组。
- cautions: 容易错的点、禁止行为、格式风险。

## 输出格式
必须只输出 JSON，不要 Markdown、解释或额外文本：
{
  "task_requirements": ["..."],
  "answering_points": ["..."],
  "evidence_plan": ["..."],
  "tool_plan": ["..."],
  "stop_conditions": ["..."],
  "answer_contract": ["..."],
  "selected_skill_ids": ["skill_id"],
  "use_short_term_memory": true,
  "selected_short_term_memory_ids": ["task_id"],
  "cautions": ["..."]
}

## 质量标准
1. 每条内容要能直接指导 generator 行动，避免空泛口号。
2. context 要短而有信息量；不要复制完整题目或完整 skill 正文。
3. selected_skill_ids 必须来自 available_skills；必须能解释为“该 skill 的触发条件正好命中当前题”。不确定时输出空数组，并依赖 task_requirements/tool_plan 说明。
4. 不要泄露或引用你不应使用的标准答案字段。
5. 不要选择泛化 skill 来补数量；上下文越短越好。
6. 每个计划项都应包含动作和判定条件，例如“若 search snippet 已含完整年份则停止”，而不是“进行搜索”。
7. 输出数组总长度控制在必要范围：普通题每类 1-3 条，复杂题也不要写成长篇教程。
8. selected_short_term_memory_ids 必须来自 short_term_memory_candidates；短期记忆只用于提醒过程风险，不得在 task_requirements 或 answering_points 中复制其答案事实。
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


def _as_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        items = [str(x).strip() for x in value if str(x).strip()]
    else:
        items = [str(value).strip()] if str(value or "").strip() else []
    return [item if item.startswith("-") else f"- {item}" for item in items]
