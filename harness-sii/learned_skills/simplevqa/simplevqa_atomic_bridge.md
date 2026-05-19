---
skill_id: simplevqa_atomic_bridge
title: SimpleVQA Atomic Fact Bridge Lookup
domains: image, simplevqa, atomic-fact, bridge-attribute, search
triggers: atomic_fact, atomic_question, source_digest, first flight year, plant family, city of plate, author died of, award count
summary: 当 SimpleVQA 先给出图像识别线索 atomic_fact，再追问该实体的年份、作者、科属、城市、奖项、疾病等外部属性时使用。
confidence: 0.88
---
# SimpleVQA Atomic Fact Bridge Lookup

Use this skill when a SimpleVQA row provides `atomic_fact`, `atomic_question`, or `source_digest`, and the user question asks for an attribute of the recognized visual entity rather than only asking what appears in the image.

## When to use
- The task contains `atomic_fact`, `atomic_question`, `source_digest`, or a similar visual recognition clue.
- The question asks a second-hop attribute: year, city/province, dynasty/era, author, publisher, inventor, plant family/order, chemical formula, award count, launch/release date, cause of death, or related person.
- The local image path is available but re-identifying the image would waste context.
- Do not use this skill for pure visual counting, color, spatial relation, or visible-text extraction.

## Diagnose / Credit Assignment
- Decide whether the answer is the visual entity itself or an attribute of that entity.
- If `atomic_fact` already matches the requested answer type, answer directly.
- If the question asks an attribute, treat `atomic_fact` as the bridge entity and do not spend steps re-identifying the image.
- Trace failures to one of four causes: ignored bridge clue, wrong relation term, answered bridge entity instead of target attribute, or repeated low-signal image/search calls.

## Evidence and Context Procedure
- Read `atomic_question` to understand what the visual clue represents, then map the user question to a target relation.
- Use `source_digest` first when it contains a page title or highlighted text that directly gives the attribute.
- Preserve entity spelling from the clue, including Latin names, punctuation, model numbers, treaty names, and bilingual names.
- If the clue is broad, add entity class as a disambiguator: plant, bridge, book, award, aircraft, chemical, historical figure, software, or artifact.
- Build a compact query as `<atomic_fact> + <target relation>`, not the whole image question.
- For taxonomy questions, query the exact rank requested: `科`, `目`, `纲`, `属`, `拉丁学名`, `family`, `order`, or `genus`.
- For year/date questions, include the event phrase: `首次飞行`, `首次发布`, `正式建立`, `开通`, `完工`, `first released`, or `launched`.

## Tool Plan
- Start with current-task compact evidence; use `search_text` only for missing external attributes.
- Use `browser_get_text` only if a promising source is authoritative but the snippet is truncated or table-like.
- Do not call `search_image` for a local image when `atomic_fact` already identifies the image content.

## Memory Layer Policy
- Short-term memory may record recent bridge misses, such as ignored `atomic_fact`, wrong relation term, or overuse of image search.
- Promote to long-term only when the update improves the general bridge procedure, taxonomy handling, query construction, or stop rule.
- Never store a specific entity-attribute pair as a durable skill fact.

## Stop / Fallback
- Stop when one authoritative source or two consistent snippets give the exact target attribute.
- After two low-signal searches, change the relation term or add the entity class; do not repeat the same query.
- If the clue is missing and the image cannot be interpreted, fall back to direct visual reasoning only when the requested answer is visible in the image.

## Output Contract
- Output only the requested attribute inside `<answer>...</answer>`.
- Do not output the bridge entity unless the question asks for it.
- Preserve requested units and granularity: `年`, full date, `位`, ordinal, province/city, taxonomy rank, or chemical formula.
