---
skill_id: twowiki_comparison
title: 2Wiki Date, Number, Lifespan, and Equality Comparison
domains: 2wiki, comparison, date-normalization, evidence-graph
triggers: comparison, came out first, first, earlier, later, older, younger, lived longer, same country, same nationality, both
summary: 当 2Wiki 问题要求比较两个实体的日期、数字、寿命、国家/国籍或相等性时使用，先标准化值再返回题目要求的实体或 yes/no。
confidence: 0.90
---
# 2Wiki Date, Number, Lifespan, and Equality Comparison

Use this skill when a 2Wiki question asks which of two entities is earlier/later/older/younger/larger, whether two entities share a property, or who lived longer.

## When to use
- The packet says `Question type: comparison` or the question contains `first`, `earlier`, `later`, `older`, `younger`, `same`, `both`, or `lived longer`.
- Evidence triples contain dates, numeric values, countries, nationalities, or comparable attributes.
- The answer should be one of the original compared entities, or `yes`/`no`.
- Do not use this skill for a simple compositional chain unless the final operation is comparison.

## Diagnose / Credit Assignment
- Identify the two compared entities from the question, not merely the subjects of date triples.
- Determine the comparison operator: earlier/first, later/newer, larger/smaller, same/different, or lifespan duration.
- Check whether a prior failure returned the intermediate person/date instead of the original compared film/book/entity.
- Check whether date strings were compared lexically instead of by normalized year/month/day.

## Evidence and Context Procedure
- Use evidence triples as the value table: entity -> predicate -> value.
- Normalize dates into comparable tuples: full date when available, year-only when that is all the packet gives.
- Normalize country/nationality aliases before equality checks, such as American -> United States and British/English -> United Kingdom.
- For lifespan questions, pair date of birth and date of death for each person before comparing durations.
- For bridge comparisons, keep a mapping from compared source entity to intermediate entity to compared value.

## Reasoning Procedure
- For `came out first` or `earlier`, choose the entity with the earliest date.
- For `later`, `newer`, or `more recent`, choose the entity with the latest date.
- For `older/younger`, decide whether the question refers to entity age, publication date, or person birth date before comparing.
- For `same country/nationality`, return `yes` only after normalized sets intersect; otherwise return `no`.
- For `lived longer`, compute death date minus birth date for each candidate and return the person with the longer duration.

## Tool Plan
- Do not search when triples provide the comparable values.
- Use supporting sentences only to resolve aliases or missing precision.
- Avoid browser/search for routine comparisons; extra context increases distractor risk.

## Memory Layer Policy
- Short-term memory may record recent comparison mistakes such as wrong operator, alias mismatch, or returning compared value instead of entity.
- Promote to long-term only when the update improves normalization, operator detection, bridge mapping, or output selection.
- Do not store specific date pairs, country facts, or comparison answers as durable memory.

## Stop / Fallback
- Stop after the normalized comparison produces one answer.
- If values are equal and the question asks whether they share a property, answer `yes`; if it asks which entity is first/later and values tie, choose only if supporting evidence resolves the tie.
- If one value is missing, use supporting sentences for the missing value before considering external tools.

## Output Contract
- Output the original entity requested by the question, not the normalized value, unless the question asks for the value.
- For boolean comparison, output exactly `yes` or `no` in lowercase.
- Wrap only the answer body in `<answer>...</answer>`.
