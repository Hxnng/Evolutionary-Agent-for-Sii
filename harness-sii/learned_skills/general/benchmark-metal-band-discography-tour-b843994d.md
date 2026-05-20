---
skill_id: benchmark-metal-band-discography-tour-b843994d
title: 金属乐队识别（出道时间+作品序列+巡演支持）
domains: general, benchmark, web, evidence
triggers: 金属乐队识别（出道时间+作品序列+巡演支持）, 题目给出乐队组建年份、各年作品类型与发行年份、为某知名乐队的某次巡演做开场, benchmark web question, external evidence lookup
summary: 题目给出乐队组建年份、各年作品类型与发行年份、为某知名乐队的某次巡演做开场
confidence: 0.70
---
# 金属乐队识别（出道时间+作品序列+巡演支持）

## When to use
- Question type: 金属乐队识别（出道时间+作品序列+巡演支持）
- Trigger: 题目给出乐队组建年份、各年作品类型与发行年份、为某知名乐队的某次巡演做开场

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：以'2013组建+2014首张EP+2016专辑+2018与2023各一张EP'为硬约束，列出符合发行节奏的金属乐队
2. 第2步：搜索'The Raven Age "Age of the Raven" tour support acts'获取该巡演开场乐队名单
3. 第3步：将两份候选交叉取交集，仅保留同时满足出道时间和巡演经历的乐队
4. 第4步：确认乐队拼写与流派标签（如melodic death metal），避免与同名其他流派乐队混淆

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
只靠'金属乐队+2013组建'搜索导致结果过多；忽略具体的作品发行年份组合
