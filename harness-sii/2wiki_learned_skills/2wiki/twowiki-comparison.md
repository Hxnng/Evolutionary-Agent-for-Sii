---
skill_id: twowiki-comparison
title: 2Wiki Direct Comparison
domains: 2wiki, comparison, date, country, equality, reasoning
triggers: comparison, born earlier, born later, older, younger, died first, died later, established first, came out first, released more recently, same nationality, same country, lived longer
summary: Procedure for direct comparison questions over dates, inception years, nationalities, countries of origin, and life spans.
confidence: 0.90
---
# 2Wiki Direct Comparison

## When to use
- Use for `type=comparison` rows where both compared entities are named directly in the question.
- Handles date ordering, age ordering, release/inception ordering, life-span duration, and equality of nationality/country.

## Diagnostic Cues
- The question asks "Who/Which was born earlier/later", "Who is older/younger", "came out first", "established first", "died first/later", "same nationality/country", or "lived longer".
- Evidence triples give one comparable value per entity, except life-span questions, which give birth and death dates for each entity.

## Evidence And Tool Plan
- Use evidence triples directly. They are cleaner than candidate context date mentions.
- Parse full dates when available; if only years exist, compare years.
- For country/nationality equality, compare the evidence values after small alias normalization only when the relation semantics allow it.

## Procedure
1. Identify the two answer candidates from the question, not from distractor context titles.
2. Map the comparator:
   - born earlier / older / born first -> earlier birth date.
   - born later / younger -> later birth date.
   - died first / died earlier -> earlier death date.
   - died later -> later death date.
   - came out first / released earlier -> earlier publication date.
   - released more recently -> later publication date.
   - established first -> earlier inception date.
   - lived longer -> compute death minus birth for each entity.
   - same nationality/country/origin -> answer `yes` if values overlap, otherwise `no`.
3. Select the entity whose value satisfies the comparator.
4. Return the candidate label in the expected answer style, often matching the question casing.

## Small-Model Thought Guide
- Make a two-row internal table: `candidate | predicate | value`.
- Decide whether the answer should be one candidate or yes/no before comparing.
- For birth-date age questions:
  - older = earlier birth date.
  - younger = later birth date.
  - born first/earlier = earlier birth date.
  - born later = later birth date.
- For release/inception:
  - came out first/established first = earlier year/date.
  - more recently = later year/date.
- For same-country questions:
  - If both sides have sets, compare set intersection.
  - `country of origin`, `country`, and `country of citizenship` are not automatically interchangeable unless the question uses that relation.
- Never answer with the compared value unless the question explicitly asks "what date/year".

## Solved Pattern Examples
- Lincoln Roberts born 4 September 1974 vs Joël Jeannot born 23 September 1965; "born earlier" -> `Joël Jeannot`.
- Manuel García Gil born 1802 vs Vasco Sousa born 1964; "born later" -> `Vasco Sousa`.
- Matija Škerbec 1886-1963 vs Ivan Minatti 1924-2012; "lived longer" -> `Ivan Minatti`.
- Julien Guerrier and Marc Pajot both French; "same nationality" -> `yes`.
- Morassa Iran vs Mamati Georgia; "same country" -> `no`.

## Stop / Fallback
- Stop once the comparator unambiguously selects an entity or yes/no.
- If one entity has multiple countries of origin, equality is `yes` when any value overlaps the other entity's value.
- Do not answer with the date itself unless the question asks for the date.

## Output Contract
- Output only `<answer>selected entity or yes/no</answer>`.
- Use lowercase `yes`/`no`.
