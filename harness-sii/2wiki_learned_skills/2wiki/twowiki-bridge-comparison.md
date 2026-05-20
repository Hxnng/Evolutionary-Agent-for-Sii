---
skill_id: twowiki-bridge-comparison
title: 2Wiki Film Director Bridge Comparison
domains: 2wiki, bridge_comparison, film, director, date, nationality, reasoning
triggers: bridge_comparison, film has the director, director born first, director died first, director older, director younger, directors same nationality, film whose director
summary: Procedure for bridge-comparison film questions: compare attributes of directors but return the original film title.
confidence: 0.92
---
# 2Wiki Film Director Bridge Comparison

## When to use
- Use for `type=bridge_comparison`, especially film questions that compare directors' birth dates, death dates, ages, or nationalities.
- The decisive trap: the compared values belong to directors, but the requested answer is the film title.

## Diagnostic Cues
- Question wording contains `Which film has the director...`, `Which film whose director...`, or asks whether two films have directors that share a nationality.
- Evidence triples usually have four edges: `film A -> director A`, `film B -> director B`, then director attributes.

## Evidence And Tool Plan
- Build a two-column table: film, director, director attribute.
- Compare only director attributes.
- Return the film whose director satisfies the comparator.

## Procedure
1. Extract the two film titles from the question.
2. Bind each film to its director via `director` triples.
3. Bind each director to the comparison attribute: date of birth, date of death, or country of citizenship.
4. Apply the comparator:
   - director older / born first / born earlier -> earlier director birth date.
   - director younger / born later -> later director birth date.
   - director died first / died earlier -> earlier director death date.
   - directors same nationality -> `yes` if citizenship values overlap, else `no`.
5. Return the film title, not the director name. For yes/no forms, return `yes` or `no`.

## Small-Model Thought Guide
- Build this internal table exactly: `film | director | director attribute | selected?`.
- Circle the answer layer before comparing. If the question begins with `Which film`, the final answer layer is film.
- `director older` means director birth date is earlier, not the film release date.
- `director died first` means director death date is earlier, not the film publication date.
- For "Do both films have directors that share the same nationality?", the film titles are not the answer candidates; the final answer is yes/no.
- After selecting a director, immediately map back through the `film -> director` edge to recover the film title.

## Solved Pattern Examples
- The Flowers of War -> Zhang Yimou born 1950; Tan de repente -> Diego Lerman born 1976; older director -> `The Flowers Of War`.
- Bad City Blues -> Michael Stevens died 2015; A Woman in White -> Claude Autant-Lara died 2000; director died first -> `A Woman In White`.
- No Highway in the Sky -> German director; Funny Face -> American director; same nationality -> `no`.

## Stop / Fallback
- Stop when the director attribute comparison selects a film.
- If evidence uses disambiguated director titles such as `(producer)` or `(director)`, accept them when the film-director triple links the person.
- If the selected evidence title differs in casing from the question, prefer the question's answer casing for local evaluation.

## Output Contract
- Output only `<answer>film title</answer>` or `<answer>yes/no</answer>`.
- Do not explain the director comparison in the final answer.
