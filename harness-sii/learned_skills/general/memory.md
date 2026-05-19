---
skill_id: memory
title: Short-Term Episodic and Long-Term Skill Memory Policy
domains: memory, context-engineering, short-term, long-term, skill-evolution
triggers: short-term memory, long-term memory, episodic trace, learned skill, memory policy, context bloat, credit assignment
summary: 区分短期轨迹记忆和长期 skill 记忆：短期用于近期路由和诊断，长期只保存稳定可迁移的上下文构造过程。
confidence: 0.90
---
# Short-Term Episodic and Long-Term Skill Memory Policy

Use this skill when deciding how generator, curator, or reflector should use prior experience without causing context bloat or turning one-off facts into durable rules.

## When to use
- The task references memory, learned skills, reflection, trajectory history, or recent failures.
- Curator must decide whether to inject recent run traces, learned skill bodies, both, or neither.
- Reflector must decide whether a lesson deserves a long-term skill update or should remain short-term episodic memory.
- The risk is overfitting to a single sample, copying a prior answer, or losing credit-assignment detail through excessive summarization.

## Diagnose / Credit Assignment
- Separate current-task evidence from prior-run evidence. Current-task evidence answers facts; memory only suggests process risks.
- Classify a lesson as short-term if it names a recent task pattern, a transient tool issue, a dataset row quirk, or a hypothesis not yet validated across tasks.
- Classify a lesson as long-term if it changes a reusable procedure for context selection, evidence filtering, tool escalation, stopping, or answer formatting.
- If a failure can be traced only to an outage, timeout, API quirk, or malformed one-off page, keep it short-term unless it teaches a reusable fallback.

## Short-Term Memory Procedure
- Store compact episodic records after each run: task family, selected skills, success/failure, tool count, repeated tools, final answer status, trajectory path, and the reflector lesson if available.
- Retrieve short-term memory only by task-family and trigger overlap; include at most a few recent traces.
- Present short-term memory as diagnostic hints, not as factual evidence. The generator must not copy answers or entities from these traces.
- Use short-term memory to avoid repeating immediate mistakes: wrong skill route, repeated low-signal tools, ignored atomic facts, or format drift.

## Long-Term Skill Memory Procedure
- Promote a lesson to long-term only after it can be written as a procedure with triggers, diagnosis, evidence/context selection, tool plan, stop/fallback conditions, and output contract.
- Merge new rules into the closest existing skill through agentic crossover: preserve effective old steps, add the new action-changing rule, and delete noisy or obsolete guidance.
- Prefer specialized skills over a bloated global memory file when the lesson is tied to a stable task family such as SimpleVQA OCR, atomic bridge lookup, Chinese culture, or direct perception.
- Keep long-term skills fact-free: no task IDs, gold answers, URLs, dataset row numbers, or one-off entity facts.

## Stop / Fallback
- Do not inject memory if the current task is simple and already has sufficient evidence.
- If short-term memory conflicts with current evidence, ignore the memory.
- If no professional long-term skill matches the task, use only the minimal init/memory guidance and solve from current evidence.

## Output Contract
- Memory content must never appear in the final user answer.
- Final answers must cite neither short-term traces nor long-term skill names.
- The only durable output of memory evolution should be improved skill files or bounded episodic records.
