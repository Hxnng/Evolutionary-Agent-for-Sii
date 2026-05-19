---
skill_id: memory
title: Long-Term Memory Skill
domains: general, memory, evidence, format
triggers: fallback, context selection, evidence gap, stop tool use, evidence, format
summary: High-quality fallback procedure for evidence selection, tool discipline, stopping, and answer control when no narrower skill applies.
confidence: 0.55
---
# Long-Term Memory Skill

## Long-Term Memory
### 适用触发 / When to use
- Use only when no narrower learned skill directly matches the task type, entity class, or failure mode.
- Use for general context risks: evidence over-selection, unnecessary tools, weak stopping, or answer-span drift.

### 失败诊断 / Credit assignment
- Identify the likely failure stage: answer type, evidence choice, tool choice, reasoning relation, stopping, or output granularity.
- Promote decision rules only; keep one-off entity facts out of long-term memory.

### 上下文/证据选择流程
- Extract answer type, core entity, target relation, and exact missing evidence.
- Prefer current-task evidence: visible/OCR text, compact hints, returned snippets/content, then browser text.
- If `atomic_fact` identifies an entity and the question asks an external attribute, use that entity plus the requested relation as the bridge.

### 工具计划
- Call tools only after naming the evidence gap.
- Prefer one targeted search query; use browser only when snippets omit or contradict the relation.

### 停止/回退条件
- Stop when evidence supports the exact requested span.
- After repeated low-signal results, change strategy once or answer from best current evidence.

### 输出格式风险
- Preserve requested language, unit, granularity, and wrapper.
- Return only the answer body inside <answer>...</answer>.
