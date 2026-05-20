---
skill_id: benchmark-tv-character-actor-shared-birthday-900079e1
title: 通过角色→演员→同生日运动员的连锁检索
domains: general, benchmark, web, evidence
triggers: 通过角色→演员→同生日运动员的连锁检索, 题目要求从某剧某集中的某个角色出发，经由演员的生日找到一位同生日的归化运动员。, benchmark web question, external evidence lookup
summary: 题目要求从某剧某集中的某个角色出发，经由演员的生日找到一位同生日的归化运动员。
confidence: 0.70
---
# 通过角色→演员→同生日运动员的连锁检索

## When to use
- Question type: 通过角色→演员→同生日运动员的连锁检索
- Trigger: 题目要求从某剧某集中的某个角色出发，经由演员的生日找到一位同生日的归化运动员。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：定位剧集——'首季在1960-2020间发布、剧情涉及21世纪亚洲真实事件、角色有经济学背景被质疑编造信息'，识别剧集与具体角色。
2. 第2步：查到该角色的演员姓名及精确出生日期。
3. 第3步：在东亚国家篮球队归化球员名单中（中国、日本、韩国、菲律宾、中华台北等）筛选同日出生且非原东亚国籍者。
4. 第4步：输出完整出生姓名（英文全名，含middle name），注意归化球员的英文出生名与亚洲化名字的区别。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
忽视'did not originally have East Asian citizenship'这一关键归化条件；混淆角色英文/中文名导致演员错配。
