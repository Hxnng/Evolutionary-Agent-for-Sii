---
skill_id: benchmark-short-edu-tv-series-localization-a69bc2ee
title: 短篇教育动画的本地化译名查询
domains: general, benchmark, web, evidence
triggers: 短篇教育动画的本地化译名查询, 题目用 1990 年代初首播、单导演双编剧、50-60 集每集<5 分钟、3 字符含数字的电视网、举办过 3 届世界杯但只有 2 届足球的国家来定位节目。, benchmark web question, external evidence lookup
summary: 题目用 1990 年代初首播、单导演双编剧、50-60 集每集<5 分钟、3 字符含数字的电视网、举办过 3 届世界杯但只有 2 届足球的国家来定位节目。
confidence: 0.70
---
# 短篇教育动画的本地化译名查询

## When to use
- Question type: 短篇教育动画的本地化译名查询
- Trigger: 题目用 1990 年代初首播、单导演双编剧、50-60 集每集<5 分钟、3 字符含数字的电视网、举办过 3 届世界杯但只有 2 届足球的国家来定位节目。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：解码线索：举办 3 届世界杯（2 届足球 + 1 届其他，如美式足球或橄榄球）→ 国家（墨西哥举办 1970/1986 足球世界杯，可能再加其他世界杯）；3 字符含数字的电视台（如 XEW、Canal 5、Once 等）。
2. 第2步：搜索 'Mexican educational animated series early 1990s short episodes twins poet living vehicle character'，定位原节目（双胞胎+诗人+抱怨者+活的交通工具+教育目的）。
3. 第3步：找到原节目后，查询其在阿根廷的发行/播出名称（可能与原名不同，常以主角名命名）。
4. 第4步：注意题目要的是'阿根廷发行名'而非原产国原名；不同国家可能有不同译名。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易直接给出墨西哥原版节目名。务必确认阿根廷播出时使用的本地化标题，可能是以主角名替换原名。
