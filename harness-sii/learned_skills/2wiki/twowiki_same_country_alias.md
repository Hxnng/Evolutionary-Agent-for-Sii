---
skill_id: twowiki_same_country_alias
title: 2Wiki Country, Nationality, and Location Alias Equality
domains: 2wiki, country-alias, equality, comparison
triggers: same country, same nationality, both from, country of citizenship, located in, nationality, American, British, English
summary: 当 2Wiki 问题判断两个实体是否同国/同国籍/同地点类别时使用，先把国籍形容词和国家名归一化再回答 yes/no。
confidence: 0.86
---
# 2Wiki Country, Nationality, and Location Alias Equality

Use this skill when the question asks whether two 2Wiki entities share a country, nationality, citizenship, or location-derived property.

## When to use
- The question contains `same country`, `same nationality`, `both from`, `are both`, or `do both`.
- Evidence triples use predicates such as country, located in, country of citizenship, nationality, birthplace, or headquarters location.
- Values may mix demonyms and country names, such as American and United States.
- Do not use this skill for date or numeric comparison.

## Diagnose / Credit Assignment
- Identify the exact property being compared: country, nationality, citizenship, location, or birthplace.
- Check whether values are demonyms, countries, regions, cities, or organizations; only compare at the requested level.
- If a prior failure answered `no` because strings differed while aliases matched, treat it as normalization failure.

## Evidence and Context Procedure
- Extract all country/nationality/location values for each compared subject from evidence triples.
- Normalize common aliases and demonyms: American/America/United States of America -> United States; British/English -> United Kingdom; Canadian -> Canada; German -> Germany; Indian -> India.
- If values are cities or regions, use supporting sentences only if the country-level mapping is explicitly available.
- Do not infer country from a city unless the packet or common dataset evidence clearly provides that mapping.

## Reasoning Procedure
- Build a set of normalized values for each subject.
- Answer `yes` if the normalized sets intersect for the requested property.
- Answer `no` if both subjects have values and no normalized intersection exists.
- If one side is missing, inspect supporting sentences before using external tools.

## Tool Plan
- Prefer evidence triples; same-country questions are usually fully represented there.
- Avoid web search unless a location-to-country mapping is absent from the packet and necessary for the answer.
- If searching, query only the missing location mapping, not the full question.

## Memory Layer Policy
- Short-term memory may record alias mismatches or city/country granularity errors.
- Promote to long-term only when the update adds a reusable alias, granularity check, or equality procedure.
- Do not store a specific entity's country as durable memory.

## Stop / Fallback
- Stop once both compared subjects have normalized comparable values.
- If the question asks `same nationality`, do not compare unrelated location predicates unless no nationality/citizenship evidence exists.
- If evidence is insufficient, answer from the best supported property and avoid unsupported inference.

## Output Contract
- Output exactly `<answer>yes</answer>` or `<answer>no</answer>` for boolean questions.
- If the question asks for the shared country/name instead, output only that normalized country/name.
