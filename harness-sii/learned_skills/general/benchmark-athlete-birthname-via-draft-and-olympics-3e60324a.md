---
skill_id: benchmark-athlete-birthname-via-draft-and-olympics-3e60324a
title: 篮球运动员全名识别
domains: general, benchmark, web, evidence
triggers: 篮球运动员全名识别, 题目提供处女座(8月下旬-9月下旬出生)、被1940年代成立的NBA球队选中、球队随迁址改名、多次代表父母出生国参加奥运会等线索，要求给出完整出生姓名, benchmark web question, external evidence lookup
summary: 题目提供处女座(8月下旬-9月下旬出生)、被1940年代成立的NBA球队选中、球队随迁址改名、多次代表父母出生国参加奥运会等线索，要求给出完整出生姓名
confidence: 0.70
---
# 篮球运动员全名识别

## When to use
- Question type: 篮球运动员全名识别
- Trigger: 题目提供处女座(8月下旬-9月下旬出生)、被1940年代成立的NBA球队选中、球队随迁址改名、多次代表父母出生国参加奥运会等线索，要求给出完整出生姓名

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：枚举1940年代成立、迁址后改名的NBA球队（如Hawks起源于Tri-Cities Blackhawks, Lakers起源于Minneapolis等），并匹配其历年新秀
2. 第2步：搜索 'Virgo NBA player drafted by Hawks/Lakers' + 'national team' + 'parents born in [country]'；过滤出生月份在处女座区间的球员
3. 第3步：候选锁定后，核验：是否至少两届奥运会出战、所代表国家是否为父母出生国、星座是否为处女座；用维基百科确认完整出生姓名（含中间名）
4. 第4步：题目要的是full birth name，必须包含中间名/教名；注意非英语国家球员的本名可能与常用名拼写不同（变音符等）

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易只给常用名而漏掉中间名；也容易把'父母出生国'误读为'本人出生国'导致错误锁定球员
