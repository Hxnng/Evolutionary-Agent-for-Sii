"""
Reflection module for failed or inefficient trajectories.

The module first tries an external OpenAI-compatible reflection call.  If that
is unavailable, it falls back to a deterministic reflection so the harness
still records useful failure analysis during offline smoke tests.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


ALLOWED_TAGS = {
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
    "simplevqa_atomic_bridge",
    "simplevqa_cn_culture_heritage",
    "simplevqa_direct_perception",
    "simplevqa_ocr_table_chart",
    "simplevqa_landmark_entity_recognition",
}
ALLOWED_SKILL_IDS = {
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
}
GENERIC_TRIGGERS = {
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
MIN_REFLECTED_BODY_CHARS = int(os.getenv("MIN_REFLECTED_SKILL_BODY_CHARS", "520"))
_WORD_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


@dataclass
class Reflection:
    failure_reason: str
    corrected_strategy: str
    reusable_memory: str
    tags: list[str]
    skill_updates: list[dict[str, Any]]

    def to_memory_fields(self) -> dict[str, Any]:
        return {
            "lesson": self.failure_reason,
            "strategy": self.corrected_strategy,
            "tags": self.tags,
        }


REFLECTION_PROMPT = """你是 reflector-agent：一个负责维护 skill 库的反思与编辑模型。

你会看到一次 generator 解题任务的题目、标准答案（如果有）、模型输出、trajectory 摘要、最近轨迹、learned_skills/SKILL.md 动态索引，以及当前可能涉及的 learned skill 摘要/片段。你的目标不是写评语，而是先根据 SKILL.md 锁定涉及的 skill，再判断这次经验应如何优化对应聚合 skill，让后续 curator-agent 能检索并使用。所有训练时产出的 skill 都应写入 learned_skills 目录；不要修改 seed skills 目录。

你的反思方式要遵循 meta context engineering / meta harness engineering 的核心原则：
- skill 是“如何构造、选择、压缩和呈现上下文”的可执行过程，不是案例记忆、答案表或短摘要。
- 不要只根据分数或最终对错写结论；必须从 trajectory 中做 credit assignment：哪一步的上下文选择、工具策略、证据过滤、答案粒度、停止条件或 curator 选择导致了失败。
- 更新时做 agentic crossover：先识别旧 skill 中仍有效的子流程，再把本次轨迹暴露的新机制合并为一个完整流程；不要追加一句 isolated lesson。
- 优先改善 accuracy/context tradeoff：减少无效工具和长上下文，同时保留足以复现成功策略的细节。
- 像 Meta-Harness 一样重视 raw trace：从最近工具调用、重复调用、错误信息、证据片段和最终输出之间建立因果链，不要只写压缩后的主观总结。
- 若 raw trajectory 证据不足以支持一个通用过程，宁可不更新 skill。
- 区分短期和长期记忆：短期记忆保存近期轨迹事实，长期记忆只保存稳定、可迁移、能改变未来上下文构造的 skill 过程。

## 工作边界
1. 你维护的是少量聚合 skill 文件，不是逐题日志。典型文件是 memory.md、search.md、format.md、tool.md、browser.md、reasoning.md、multihop.md、image.md 等。
2. 不要把本题标准答案、具体 benchmark 答案、一次性实体事实写入 skill。
3. 每次先读 learned_skills/SKILL.md 的索引说明，直接定位涉及的能力 skill；再结合提供的对应 skill 正文片段进行完整更新。
4. 每次只优化“涉及到的能力 skill”。如果错误来自搜索策略，就更新 search；来自答案格式，就更新 format；来自通用经验沉淀，就更新 memory；来自多跳推理，就更新 multihop。
5. 允许三类操作，目标都是 learned_skills/*.md：
   - add: 当该聚合 skill 尚不存在时创建它，例如 search.md 或 memory.md。
   - update: 当该聚合 skill 已存在时重写为更好的完整 skill 正文。
   - delete: 删除明显误导、重复、过时或有害的 skill。
6. 如果失败是偶然接口错误、无可迁移经验，skill_updates 可以为空。
7. skill body 要像可直接拼进 generator context 的小型说明：说明何时使用、如何诊断、怎么做、何时停止/回退、最终答案如何约束，不要写成事后感想。
8. 更新已有 skill 时要“整合旧内容 + 新经验”，输出完整替换正文；不要只追加一条孤立 bullet。
9. skill body 必须包含这些结构，标题可中英混用但含义必须齐全：适用触发、失败诊断/credit assignment、上下文/证据选择流程、工具计划、停止/回退条件、输出格式风险。
10. 禁止写入本题答案、题目专属实体名、task_id、数据集行号、URL碎片或“这道题应该答 X”。
11. 如果你只能写出少于 7 条可迁移步骤的内容，skill_updates 应为空。
12. skill 必须有强指向性：summary 写“什么任务/风险触发它”，triggers 写具体短语或模式，不要只写 search、reasoning、format、tool 这类泛标签。
13. domains 至少包含一个能力标签和一个任务/数据形态标签，例如 ["search", "award-count"]、["image", "local-image"]、["multihop", "bridge-entity"]。不要只给 ["reasoning"]。
14. body 中不要出现“本题”“这道题”“上一次”“标准答案”等只对当前样本有效的话；要写成 generator 下次可执行的通用操作规程。
15. 若经验只适合近期相似样本，不足以成为长期 skill，skill_updates 必须为空；它会留在 short-term episodic memory，不要强行写入 learned skill。

## 判断重点
- failure_reason: 本次失败/低效最核心的根因，用于轨迹审计。
- corrected_strategy: 下次遇到同类任务时应该采取的可执行策略。
- skill_updates: 对 skill 库的最小必要修改。宁可少改，不要制造噪声。每个 update 都必须显式提升一个可复用能力，而不是记录一次经历。

## 反思流程
1. 定位失败阶段：理解题意、上下文选择、证据检索、工具执行、推理组合、答案格式、停止条件。
2. 检查 trajectory：引用最近轨迹中的行为模式，但不要在输出中泄露长日志。
3. 选择 skill：只选一个主 skill；除非有明确耦合，不要同时更新多个 skill。
4. 设计更新：把旧 skill 的有效内容和本次新规则合并成完整、短而有层次的说明；保留能决定检索/工具/输出行为的细节，删除题目事实。
5. 自检：若 body 含具体答案、实体事实、过窄场景、低于可迁移门槛或会增加上下文噪声，放弃该 update。

## 输出格式
必须只输出 JSON，不要 Markdown、解释或额外文本：
{
  "failure_reason": "一句话说明根因，仅用于轨迹审计",
  "corrected_strategy": "30-80字，可复用、可执行，不复述本题答案",
  "reusable_memory": "同 corrected_strategy，可略短",
  "tags": ["format", "search"],
  "skill_updates": [
    {
      "op": "update",
      "skill_id": "search",
      "title": "Search Skill",
      "domains": ["search", "reasoning"],
      "triggers": ["获奖人数", "winners list", "site:official-domain"],
      "summary": "当题目要求统计特定奖项/年份的获奖人数且搜索结果可能混杂时使用",
      "body": "完整 skill 正文，必须包含：适用触发；失败诊断/credit assignment；上下文/证据选择流程；工具计划；停止/回退条件；答案格式风险。",
      "confidence": 0.65
    }
  ]
}

## 字段规则
1. tags 只能从以下集合中选择 1-3 个最关键标签：
   format, search, browser, tool, ocr, image, entity, multihop, evidence, efficiency, reasoning
2. skill_id 必须是聚合能力名之一：
   memory, search, browser, tool, format, ocr, image, entity, multihop, evidence, efficiency, reasoning
   或已存在的专业 learned skill，例如 simplevqa_atomic_bridge, simplevqa_cn_culture_heritage, simplevqa_direct_perception, simplevqa_ocr_table_chart, simplevqa_landmark_entity_recognition。
3. 不要输出 memory.search.xxx、case_xxx、task_xxx 这类逐题 skill_id；专业 skill_id 必须对应稳定题型，而不是单个样本。
4. 如果目标 skill 已存在，使用 op=update；如果不存在，使用 op=add。body 必须是完整替换正文，不是 diff 片段。
5. delete 只需要 op 和 skill_id；只能删除 learned skill，不要删除 init_skill。
6. confidence 使用 0.50-0.90；越通用、证据越充分越高。
"""


def _json_from_text(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _clamp_confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.65
    return max(0.50, min(0.90, score))


def _clean_tags(values: Any) -> list[str]:
    tags: list[str] = []
    raw = values if isinstance(values, list) else [values]
    for item in raw:
        tag = str(item or "").strip().lower()
        if tag in ALLOWED_TAGS and tag not in tags:
            tags.append(tag)
    return tags[:3] or ["reasoning"]


def _specific_values(values: Any) -> list[str]:
    raw = values if isinstance(values, list) else [values]
    clean: list[str] = []
    for item in raw:
        text = str(item or "").strip().lower()
        if not text or text in GENERIC_TRIGGERS:
            continue
        if len(text) < 3 and not any("\u4e00" <= ch <= "\u9fff" for ch in text):
            continue
        if text not in clean:
            clean.append(text)
    return clean


def _canonical_skill_id(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    if text in ALLOWED_SKILL_IDS:
        return text
    if "." in text:
        first = text.split(".", 1)[0]
        if first in ALLOWED_SKILL_IDS:
            return first
    return ""


def _text_tokens(text: str) -> set[str]:
    return {x.lower() for x in _WORD_RE.findall(text or "") if len(x.strip()) > 1}


def _looks_like_actionable_skill(body: str) -> bool:
    if len(body.strip()) < MIN_REFLECTED_BODY_CHARS:
        return False
    markers = (
        "when",
        "use",
        "step",
        "stop",
        "fallback",
        "output",
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
    )
    lowered = body.lower()
    marker_hits = sum(1 for marker in markers if marker in lowered)
    bullet_hits = len(re.findall(r"(?m)^\s*(?:[-*]|\d+[.、])\s+", body))
    required_groups = (
        ("适用", "触发", "when to use", "use when"),
        ("诊断", "判断", "credit assignment", "failure"),
        ("流程", "步骤", "procedure", "workflow"),
        ("停止", "回退", "stop", "fallback"),
        ("输出", "格式", "answer contract", "output"),
    )
    has_shape = all(any(token in lowered for token in group) for group in required_groups)
    return marker_hits >= 6 and bullet_hits >= 6 and has_shape


def _contains_forbidden_case_fact(body: str, instruction: str, pred: str, answer: str) -> bool:
    lowered = (body or "").lower()
    forbidden_markers = (
        "本题",
        "这道题",
        "该题",
        "标准答案",
        "gold answer",
        "task_id",
        "trajectory",
        "上一次",
        "此次",
        "url:",
        "http://",
        "https://",
    )
    if any(marker in lowered for marker in forbidden_markers):
        return True
    body_tokens = _text_tokens(body)
    if not body_tokens:
        return True
    for value in (answer, pred):
        value = str(value or "").strip()
        if len(value) >= 3 and value in body:
            return True

    instruction_tokens = _text_tokens(instruction)
    if not instruction_tokens:
        return False
    overlap = body_tokens & instruction_tokens
    # A high overlap usually means the body copied the case rather than
    # abstracting the behavior. Keep the threshold loose for Chinese tasks.
    return len(overlap) >= 10 and len(overlap) / max(1, len(body_tokens)) > 0.18


def _sanitize_skill_updates(
    raw_updates: Any,
    *,
    instruction: str,
    pred: str,
    answer: str,
    skill_context: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    existing_ids = {str(skill.get("skill_id") or "").strip().lower() for skill in (skill_context or [])}
    updates: list[dict[str, Any]] = []
    if not isinstance(raw_updates, list):
        return updates
    for raw in raw_updates:
        if not isinstance(raw, dict):
            continue
        op = str(raw.get("op") or "add").strip().lower()
        if op not in {"add", "update", "delete"}:
            continue
        skill_id = _canonical_skill_id(raw.get("skill_id"))
        if not skill_id or skill_id == "init_skill":
            continue
        if op == "delete":
            updates.append({"op": "delete", "skill_id": skill_id})
            continue

        body = str(raw.get("body") or raw.get("content") or "").strip()
        if not _looks_like_actionable_skill(body):
            continue
        if _contains_forbidden_case_fact(body, instruction, pred, answer):
            continue

        # Reflector sometimes says "add" for an existing learned skill. Keep the
        # operation aligned with the current skill index to avoid duplicate intent.
        normalized_op = "update" if skill_id in existing_ids else op
        domains = _clean_tags(raw.get("domains") or raw.get("tags"))
        specific_domains = _specific_values(raw.get("domains"))
        triggers = [
            str(x).strip()
            for x in (raw.get("triggers") if isinstance(raw.get("triggers"), list) else domains)
            if str(x).strip()
        ][:12]
        specific_triggers = _specific_values(triggers)
        if not specific_triggers and not specific_domains:
            continue
        if specific_domains:
            domains = list(dict.fromkeys(domains + specific_domains[:3]))
        updates.append(
            {
                "op": normalized_op,
                "skill_id": skill_id,
                "title": str(raw.get("title") or f"{skill_id.title()} Skill").strip(),
                "domains": domains,
                "triggers": specific_triggers[:12] or specific_domains[:8],
                "summary": str(raw.get("summary") or f"Reusable {skill_id} procedure.").strip()[:220],
                "body": body,
                "confidence": _clamp_confidence(raw.get("confidence")),
            }
        )
    return updates[:2]


def _fallback_skill_body(skill_id: str, strategy: str) -> str:
    focus = {
        "search": "external fact lookup, source choice, query refinement, and snippet-to-answer extraction",
        "tool": "tool selection, retry limits, argument repair, and switching away from repeated failures",
        "format": "answer granularity, wrapper compliance, and preventing explanatory leakage",
        "image": "visual evidence routing, atomic_fact usage, and image-search fallback decisions",
        "multihop": "bridge-entity decomposition, supporting evidence ordering, and relation composition",
        "evidence": "evidence sufficiency, contradiction checks, and deciding when context already answers",
        "efficiency": "context budget, stopping rules, and avoiding repeated low-signal actions",
        "reasoning": "entity-relation decomposition, local inference, and controlled use of tools",
    }.get(skill_id, "general context selection and answer control")
    return (
        f"Use this skill when the task exposes a reusable {skill_id} failure mode involving {focus}.\n\n"
        "## When to use\n"
        f"- The trajectory shows uncertainty, wrong context selection, repeated tools, weak evidence filtering, or output drift related to {skill_id}.\n"
        "- The lesson can change future generator behavior across tasks, not just explain one sample.\n"
        "- A narrower learned skill does not already cover the exact trigger.\n\n"
        "## Diagnose / Credit Assignment\n"
        "- Identify the first step where the generator had enough context but chose the wrong action, or lacked a specific piece of evidence.\n"
        "- Separate evidence failure from tool failure, reasoning failure, and answer-format failure.\n"
        "- Name the missing decision in one sentence before adding any new context.\n\n"
        "## Procedure\n"
        "- Extract the requested answer type, core entity, relation, and required granularity.\n"
        f"- Apply this transferable tactic: {strategy}\n"
        "- Prefer current-task compact evidence before external tools; use tools only for the unresolved gap.\n"
        "- When using tools, issue one high-signal query or action that targets the missing decision directly.\n"
        "- Compare returned evidence against the original question before accepting nearby entities, broader categories, or partial dates.\n"
        "- Preserve useful existing skill structure and add only the smallest rule that changes a future action.\n\n"
        "## Stop / Fallback\n"
        "- Stop once compact evidence or two independent signals resolve the exact requested span.\n"
        "- After two low-signal or repeated tool results, change the query/tool or answer from the best available evidence with the correct granularity.\n"
        "- If the failure came from an external outage, do not create a new skill unless the fallback behavior is reusable.\n\n"
        "## Output Contract\n"
        "- Put only the requested answer body inside <answer>...</answer> unless the task explicitly asks for more.\n"
        "- Do not mention this skill, the reflector, trajectory, gold answer, or hidden context in the final answer."
    )


def _fallback_reflection(
    instruction: str,
    pred: str,
    answer: str = "",
    trajectory_summary: dict[str, Any] | None = None,
) -> Reflection:
    summary = trajectory_summary or {}
    role_counts = summary.get("role_counts", {})
    tool_turns = int(role_counts.get("tool", 0))

    if not pred.strip():
        reason = "模型没有给出有效最终答案，可能在工具循环或格式控制上失败。"
        strategy = "设置更明确的 <answer> 输出约束；接近最大轮数时停止搜索并归纳已有证据。"
        tags = ["format", "reasoning"]
    elif answer and pred.strip() != answer.strip():
        reason = "最终答案与标准答案不一致，可能是证据不足、检索方向错误或多跳关系没有核验。"
        strategy = "先识别实体和关系，再用搜索或浏览器交叉验证关键事实，最后只输出答案本体。"
        tags = ["search", "reasoning"]
    elif tool_turns > 6:
        reason = "工具调用轮数偏多，存在低效搜索或重复浏览。"
        strategy = "每次搜索前明确缺口，优先使用高信息量查询，并在两次无增益后切换策略。"
        tags = ["tool", "efficiency"]
    else:
        reason = "任务完成但仍可沉淀经验，用于减少后续无效推理。"
        strategy = "保留成功查询、实体消歧和答案格式经验，后续相似任务优先复用。"
        tags = ["efficiency", "reasoning"]

    if "image" in instruction.lower() or "图" in instruction:
        tags.append("image")
    if "wiki" in instruction.lower() or "多跳" in instruction:
        tags.append("multihop")

    tags = [tag for tag in tags if tag in ALLOWED_TAGS]
    primary_tag = tags[0] if tags else "reasoning"
    skill_id = primary_tag if primary_tag in ALLOWED_SKILL_IDS - {"memory"} else "memory"
    return Reflection(
        failure_reason=reason,
        corrected_strategy=strategy,
        reusable_memory=f"{reason} {strategy}",
        tags=tags,
        skill_updates=[
            {
                "op": "update",
                "skill_id": skill_id,
                "title": f"{skill_id.title()} Skill",
                "domains": tags[:3],
                "triggers": tags[:3] + [primary_tag],
                "summary": f"Reusable tactics for {skill_id} failures.",
                "body": _fallback_skill_body(skill_id, strategy),
                "confidence": 0.6,
            }
        ],
    )


def reflect(
    instruction: str,
    pred: str,
    answer: str = "",
    trajectory: list[dict[str, Any]] | None = None,
    trajectory_summary: dict[str, Any] | None = None,
    skill_manifest: str = "",
    skill_context: list[dict[str, Any]] | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> Reflection:
    """Return a structured reflection for later memory updates."""
    if os.getenv("DISABLE_REFLECTION_LLM", "0") == "1":
        return _fallback_reflection(instruction, pred, answer, trajectory_summary)

    base_url = base_url or os.getenv("REFLECTION_BASE_URL") or os.getenv(
        "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    model_name = model_name or os.getenv("REFLECTION_MODEL_NAME") or os.getenv("MODEL_NAME", "qwen3.5-35b-a3b")
    api_key = api_key or os.getenv("REFLECTION_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_reflection(instruction, pred, answer, trajectory_summary)

    compact_traj = []
    for row in (trajectory or [])[-12:]:
        compact_traj.append(
            {
                "step_id": row.get("step_id"),
                "role": row.get("role"),
                "content": str(row.get("content", ""))[:1200],
                "fn_name": row.get("fn_name"),
            }
        )

    user = {
        "instruction": instruction,
        "answer": answer,
        "pred": pred,
        "trajectory_summary": trajectory_summary or {},
        "recent_trajectory": compact_traj,
        "learned_skill_index": skill_manifest,
        "existing_learned_skills": skill_context or [],
    }
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": REFLECTION_PROMPT},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.2,
            extra_body={"enable_thinking": False},
        )
        data = _json_from_text(resp.choices[0].message.content or "")
        tags = _clean_tags(data.get("tags", []))
        skill_updates = _sanitize_skill_updates(
            data.get("skill_updates", []),
            instruction=instruction,
            pred=pred,
            answer=answer,
            skill_context=skill_context,
        )
        return Reflection(
            failure_reason=str(data.get("failure_reason", "")).strip(),
            corrected_strategy=str(data.get("corrected_strategy", "")).strip(),
            reusable_memory=str(data.get("reusable_memory", "")).strip(),
            tags=tags,
            skill_updates=skill_updates,
        )
    except Exception:
        return _fallback_reflection(instruction, pred, answer, trajectory_summary)
