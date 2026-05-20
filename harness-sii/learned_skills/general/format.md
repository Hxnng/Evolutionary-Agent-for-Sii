---
skill_id: format
title: Format Skill
domains: format, reasoning
triggers: format, reasoning
summary: Reusable tactics for format failures.
confidence: 0.60
---
# Format Skill

Use this skill when the task exposes a reusable format failure mode involving answer granularity, wrapper compliance, and preventing explanatory leakage.

## When to use
- The trajectory shows uncertainty, wrong context selection, repeated tools, weak evidence filtering, or output drift related to format.
- The lesson can change future generator behavior across tasks, not just explain one sample.
- A narrower learned skill does not already cover the exact trigger.

## Diagnose / Credit Assignment
- Identify the first step where the generator had enough context but chose the wrong action, or lacked a specific piece of evidence.
- Separate evidence failure from tool failure, reasoning failure, and answer-format failure.
- Name the missing decision in one sentence before adding any new context.

## Procedure
- Extract the requested answer type, core entity, relation, and required granularity.
- Apply this transferable tactic: 设置更明确的 <answer> 输出约束；接近最大轮数时停止搜索并归纳已有证据。
- Prefer current-task compact evidence before external tools; use tools only for the unresolved gap.
- When using tools, issue one high-signal query or action that targets the missing decision directly.
- Compare returned evidence against the original question before accepting nearby entities, broader categories, or partial dates.
- Preserve useful existing skill structure and add only the smallest rule that changes a future action.

## Stop / Fallback
- Stop once compact evidence or two independent signals resolve the exact requested span.
- After two low-signal or repeated tool results, change the query/tool or answer from the best available evidence with the correct granularity.
- If the failure came from an external outage, do not create a new skill unless the fallback behavior is reusable.

## Output Contract
- Put only the requested answer body inside <answer>...</answer> unless the task explicitly asks for more.
- Do not mention this skill, the reflector, trajectory, gold answer, or hidden context in the final answer.
