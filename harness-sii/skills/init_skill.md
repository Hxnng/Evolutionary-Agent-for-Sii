---
skill_id: init_skill
title: Initial Task Solving Skill
domains: general, simplevqa, 2wiki
triggers: task, answer, tool, evidence, format, skill
summary: General startup guidance for generator before specialized learned skills exist.
confidence: 1.00
---
# Initial Task Solving Skill

Use this skill when no more specific learned skill clearly applies.

1. Read the task carefully and identify exactly what answer type is requested: entity, attribute, date, count, location, yes/no, comparison, or multi-hop target.
2. Treat curator context, dataset hints, and learned skills as guidance, not as guaranteed facts. Verify factual claims against current-task evidence.
3. Use the smallest sufficient evidence path. If compact evidence such as `atomic_fact`, `source_digest`, evidence triples, or supporting sentences is enough, answer without extra tool calls.
4. Use tools only to close a specific evidence gap. Prefer `search_text` first for factual lookup; use browser tools only when search snippets/content are insufficient; use image search only when a usable http(s) image URL is available and visual recognition is uncertain.
5. Stop tool use after repeated low-signal results. Switch query strategy or answer from the best available evidence instead of looping.
6. Preserve the answer granularity requested by the question. Do not output a broader entity, longer explanation, or nearby synonym when the question asks for a short span.
7. Final answer must be concise and wrapped in `<answer>...</answer>`.
