"""
Reflection module for failed or inefficient trajectories.

The module first tries an external OpenAI-compatible reflection call.  If that
is unavailable, it falls back to a deterministic reflection so the harness
still records useful failure analysis during offline smoke tests.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass
class Reflection:
    failure_reason: str
    corrected_strategy: str
    reusable_memory: str
    tags: list[str]

    def to_memory_fields(self) -> dict[str, Any]:
        return {
            "lesson": self.failure_reason,
            "strategy": self.corrected_strategy,
            "tags": self.tags,
        }


REFLECTION_PROMPT = """你是 Harness Engineering 的反思模块。请基于任务、标准答案、模型输出和轨迹摘要，分析失败或低效原因。
必须输出 JSON，不要输出 Markdown：
{
  "failure_reason": "一句话说明根因",
  "corrected_strategy": "下次遇到类似任务应该怎么做",
  "reusable_memory": "可沉淀到长期记忆的一条经验",
  "tags": ["simplevqa|2wiki|search|browser|tool|reasoning|format"]
}
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
        tags = ["success", "reasoning"]

    if "image" in instruction.lower() or "图" in instruction:
        tags.append("simplevqa")
    if "wiki" in instruction.lower() or "多跳" in instruction:
        tags.append("2wiki")

    return Reflection(
        failure_reason=reason,
        corrected_strategy=strategy,
        reusable_memory=f"{reason} {strategy}",
        tags=tags,
    )


def reflect(
    instruction: str,
    pred: str,
    answer: str = "",
    trajectory: list[dict[str, Any]] | None = None,
    trajectory_summary: dict[str, Any] | None = None,
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
        return Reflection(
            failure_reason=str(data.get("failure_reason", "")).strip(),
            corrected_strategy=str(data.get("corrected_strategy", "")).strip(),
            reusable_memory=str(data.get("reusable_memory", "")).strip(),
            tags=[str(x) for x in data.get("tags", []) if str(x).strip()],
        )
    except Exception:
        return _fallback_reflection(instruction, pred, answer, trajectory_summary)
