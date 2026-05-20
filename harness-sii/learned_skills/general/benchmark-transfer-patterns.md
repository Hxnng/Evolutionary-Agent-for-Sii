---
skill_id: benchmark-transfer-patterns
title: Benchmark Transfer Patterns
domains: general, benchmark, web, evidence, reasoning
triggers: benchmark-like question, multi-constraint lookup, hidden entity identification, answer shape calibration, evidence discipline, unverifiable detail
summary: Distilled benchmark-style lookup patterns for multi-constraint web questions, preserving reusable reasoning and answer-shape calibration without storing benchmark answers.
confidence: 0.78
---
# Benchmark Transfer Patterns

## When to use
- Use for benchmark-like questions that hide the target entity behind multiple biographical, corporate, media, sports, academic, or historical constraints.
- Use when the task asks for a small final span: a name, date, title, count, company, production credit, species, or "无法确定".
- Prefer a narrower skill when one directly matches the domain; use this as a fallback pattern when no specific skill is strong enough.

## Diagnostic Cues
- The prompt contains stacked constraints with date ranges, role chains, family links, publication histories, institutional founding dates, match stats, or report references.
- The final answer depends on first identifying an entity, then extracting one exact attribute from a reliable source.
- Some tasks are intentionally unanswerable because the requested detail is private, unpublished, or not uniquely supported.

## Evidence And Tool Plan
- Split the problem into anchors: entity class, time window, distinctive facts, bridge relation, and requested answer type.
- Search with the rarest stable anchors first. Combine two or three anchors, not the entire prompt.
- After a candidate appears, verify it against the original constraints before extracting the final attribute.
- Prefer primary or near-primary sources: annual reports, official bios, episode guides, competition records, theses, interviews, institutional pages, archived articles, and specialist databases.
- If sources disagree, trust the source closest to the asserted relation and preserve the requested granularity.

## Procedure
1. Build a compact clue table mentally: `target type -> anchor facts -> bridge entity -> requested attribute`.
2. Use the answer shape to constrain search. A share count needs filings; a spouse first name needs a biography/interview; a release title needs localization databases; a "third substitute" needs a match report or lineup table.
3. Confirm the candidate with at least two independent clues before opening a broad page or accepting a snippet.
4. Extract only the requested span. Do not carry extra context, honorifics, surnames, units, or explanations unless the task asks for them.
5. For privacy-sensitive or trivial personal details, require explicit public evidence. If the trail only proves the surrounding entity but not the requested detail, answer as indeterminate.

## Calibration Examples
- Corporate filing questions often end with a precise numeric balance or count; the decisive evidence is usually a dated annual report table or note, not a news article.
- Biography-chain questions usually end with a full name, birth name, sibling name, or spouse name; the decisive evidence is the page that states the exact relationship.
- Media and sports questions often use episode, match, or production fingerprints; the decisive evidence is a roster, credits page, episode synopsis, or database entry matching the full event.
- Academic/thesis questions often require repository PDFs and acknowledgments or references; search snippets rarely contain the answer.
- If the final attribute is not a normal public fact, the correct behavior may be "无法确定" rather than a guessed entity.

## Stop / Fallback
- Stop when the candidate satisfies the anchors and a reliable source supports the exact final span.
- If searches return only near matches, change the anchor mix once: use a rare phrase, a date plus entity class, or the expected source type.
- After repeated weak evidence, output the best supported indeterminate answer instead of inventing a span.

## Output Contract
- Return only the answer body inside `<answer>...</answer>`.
- Do not mention benchmark files, training data, skill IDs, gold answers, or internal routing.
