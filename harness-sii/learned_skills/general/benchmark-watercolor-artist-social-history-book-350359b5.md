---
skill_id: benchmark-watercolor-artist-social-history-book-350359b5
title: 通过艺术家生平定位包含其传记的合集书名
domains: general, benchmark, web, evidence
triggers: 通过艺术家生平定位包含其传记的合集书名, 已知某业余艺术家的婚姻年、无子女、卒年，需要找一本2010s社会史合集书的标题。, benchmark web question, external evidence lookup
summary: 已知某业余艺术家的婚姻年、无子女、卒年，需要找一本2010s社会史合集书的标题。
confidence: 0.70
---
# 通过艺术家生平定位包含其传记的合集书名

## When to use
- Question type: 通过艺术家生平定位包含其传记的合集书名
- Trigger: 已知某业余艺术家的婚姻年、无子女、卒年，需要找一本2010s社会史合集书的标题。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：用'1894年结婚、无子女、1961年去世、业余水彩画家、30幅原作展出于2015-2020'锁定该艺术家姓名。
2. 第2步：用艺术家姓名+'fourteen lives'/'social history'/'pioneers'等关键词搜索2010年代出版的传记合集。
3. 第3步：在Google Books或亚马逊上验证该书目录确实包含此艺术家。
4. 第4步：输出完整书名（含副标题），合集类书籍主标题往往有戏剧化主标题+列举式副标题。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
只输出主标题而漏掉副标题；将艺术家自身的传记书与含其在内的合集书混淆。
