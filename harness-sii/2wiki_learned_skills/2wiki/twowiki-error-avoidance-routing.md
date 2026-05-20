---
skill_id: twowiki-error-avoidance-routing
title: 2Wiki Error Avoidance And Routing Guide
domains: 2wiki, routing, error, reasoning, evidence, format
triggers: wrong answer layer, alias mismatch, comparison direction error, distractor context, small model guidance, avoid mistakes, evidence triples
summary: Concentrated small-model routing and error-avoidance guide distilled from solving the 100 local 2wiki rows.
confidence: 0.88
---
# 2Wiki Error Avoidance And Routing Guide

## When to use
- Use whenever a 2Wiki task looks easy but could fail through answer-layer confusion, comparison-direction reversal, or noisy candidate context.
- Use together with a narrower skill when the model is small, near step limit, or repeatedly outputs the first plausible entity.
- This skill is especially useful before final answer generation.

## Diagnose / Credit Assignment
- If the model answered a person for a `Where` question, the failure is answer-layer control.
- If the model answered a director for a `Which film` bridge question, the failure is bridge return mapping.
- If the model answered the date/year for a comparison question, the failure is answer-candidate control.
- If the model answered `no` despite one overlapping country in multi-origin evidence, the failure is set comparison.
- If the model used a same-name distractor document, the failure is title/focus discipline.

## Routing Heuristics

### Route by question surface
- `Where was the director of film... born?` -> `twowiki-multihop-chain`.
- `What nationality is the director/spouse/father...` -> `twowiki-multihop-chain`.
- `Who is the paternal grandfather / maternal grandmother / father-in-law...` -> `twowiki-kinship-inference`.
- `Who did X marry?` with child/father/mother edges -> `twowiki-kinship-inference`.
- `Who/Which was born earlier/later`, `older/younger`, `died first/later`, `came out first`, `established first`, `same country` -> `twowiki-comparison`.
- `Which film has the director...` -> `twowiki-bridge-comparison`.

### Route by evidence shape
- Two triples where second subject equals first object -> compositional chain.
- Two `father/mother/spouse/child` triples -> kinship inference.
- Two triples with same predicate and two different subjects -> direct comparison.
- Four triples: two `director` edges plus two date/country edges -> bridge comparison.
- Four date triples with birth/death for two people -> lived-longer comparison.

## Small-Model Safety Checklist

Before finalizing, answer these internally:

1. What is the final answer layer: person, place, date, movie, organization, yes/no?
2. Did I use the second-hop object when the question asks an attribute?
3. If I compared an intermediate entity, did I map back to the original entity?
4. Did I apply the comparison direction correctly?
5. Did I preserve the answer span's spelling, diacritics, date granularity, and yes/no casing?

If any answer is uncertain, do not search broadly. Re-read the evidence triples and the exact question wording.

## Error Patterns From The 100 Solved Rows

### 1. Answer-layer mismatch
- Rows like 1, 8, 10, 17, 34 ask for director birthplace. The director is never the final answer.
- Rows like 6, 15, 21, 23, 24, 26, 30, 41, 52, 67, 72, 76, 90, 92, 97, 98 compare directors but answer films.
- Rows like 3, 53, 66, 77, 87, 88, 91 ask for a relative/award of the intermediate person, not the film/song.

### 2. Comparison direction reversal
- `older` and `born earlier` both mean smaller/earlier birth date.
- `younger` and `born later` mean larger/later birth date.
- `died first` means earlier death date; `died later` means later death date.
- `came out first` and `established first` mean earlier publication/inception.
- `more recently` means later publication.

### 3. Multi-value equality
- Row 35 has The Woman in the Fifth with multiple origins. Because British overlaps with Evensong's British origin, answer is `yes`.
- Do not demand exact set equality unless the question says identical set.

### 4. Alias and disambiguation
- Row 56 has a father alias mismatch: question/evidence may show Thoros III and Thoros I around Leo III. Trust the supplied evidence chain when it resolves the requested date.
- Director pages may be disambiguated with `(producer)` or `(director)`. If the film-director triple points there, use that page's date/country.
- Question casing can be unusual: `It'S`, `The Stranger'S`, `Matthew'S`. Preserve expected title style when possible.

### 5. Nationality/country wording
- `country of citizenship` values may be adjectival: `French`, `American`, `German`.
- `country` values may be place names: `Iran`, `Georgia`.
- `country of origin` values for films may be adjectival: `British`, `Australian`.
- Output the evidence value as written for attribute questions. For equality questions, compare semantically only inside the decision.

## Tool Plan
- For local evaluation rows, evidence triples are enough. Tool use normally wastes budget and increases drift.
- Use browser/search only when context is truncated or missing the second edge.
- If a tool is used, query one exact pair: `"entity" "relation phrase"`; then stop when the missing relation is found.

## Stop / Fallback
- Stop immediately after the selected entity/value satisfies the question layer.
- If two skills could apply, prefer the one matching the evidence shape over one matching a generic word.
- If the final answer candidate is a date but the question begins with `Who/Which film/Which one`, re-evaluate: comparison questions usually want an entity, not a value.

## Output Contract
- Output exactly `<answer>...</answer>`.
- No explanation, no evidence trace, no skill name, no row number.
