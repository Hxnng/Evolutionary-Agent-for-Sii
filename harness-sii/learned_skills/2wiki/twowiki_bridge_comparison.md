---
skill_id: twowiki_bridge_comparison
title: 2Wiki Bridge Comparison Source-Entity Mapping
domains: 2wiki, bridge-comparison, comparison, multihop
triggers: bridge_comparison, director of film, author of book, publication date, date of birth, came out first, which film, which book
summary: 当 2Wiki 问题先从两个源实体桥接到人物/属性再比较时使用，避免返回中间实体而忘记映射回原始电影/书籍/作品。
confidence: 0.88
---
# 2Wiki Bridge Comparison Source-Entity Mapping

Use this skill when a 2Wiki question compares attributes reached through bridge entities, especially when the answer should be the original film/book/work rather than the intermediate person or date.

## When to use
- The packet says `Question type: bridge_comparison`.
- The question compares films/books/works through their directors, authors, actors, release dates, birth dates, or death dates.
- Evidence triples include source-to-bridge edges and bridge-to-value edges.
- Do not use this skill for direct comparison where the compared entity itself owns the comparable value.

## Diagnose / Credit Assignment
- Identify source entities named in the question.
- For each source entity, identify its bridge entity and then the value used for comparison.
- Preserve a source -> bridge -> value table throughout reasoning.
- If a prior answer returns the bridge person or date, treat it as source-mapping failure.

## Evidence and Context Procedure
- Build rows with three columns: source entity, bridge entity, comparable value.
- Use predicates such as director, author, performer, publication date, date of birth, date of death, place of birth, or award received to fill the table.
- If a value triple's subject is the bridge entity, map the comparison result back to the source entity whose bridge matched it.
- Use supporting sentences only when a source title or bridge alias differs slightly from the triple.

## Reasoning Procedure
- Determine the comparison operator from the question.
- Compare normalized values using the 2Wiki comparison skill's date/number/alias rules.
- After choosing a winning bridge/value, return the corresponding source entity if the question asks which film/book/work/source item.
- Return the bridge entity only when the question explicitly asks for the person or intermediate entity.

## Tool Plan
- Stay inside the context packet when source, bridge, and value triples are present.
- Do not search for release dates or birth dates already present in triples.
- If one bridge edge is missing, inspect supporting sentences for the source title before external lookup.

## Memory Layer Policy
- Short-term memory may store recent source/bridge mapping misses.
- Promote to long-term only when the update improves table construction, alias mapping, or output entity selection.
- Do not store source-to-bridge facts from a particular row in long-term memory.

## Stop / Fallback
- Stop once every compared source has a comparable value and the winning source is determined.
- If the question wording asks for `which film/book`, never stop with a person/date answer.
- If the compared values are unsupported, return the best supported source only after checking supporting sentences.

## Output Contract
- Output exactly the source entity or requested bridge/value inside `<answer>...</answer>`.
- Do not include the comparison table or explanation.
