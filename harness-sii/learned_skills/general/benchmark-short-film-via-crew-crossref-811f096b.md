---
skill_id: benchmark-short-film-via-crew-crossref-811f096b
title: 短片识别（多重剧组+学历线索）
domains: general, benchmark, web, evidence
triggers: 短片识别（多重剧组+学历线索）, 题目给出短片时长、年份、剧情梗概，并通过导演学历和剪辑师另一部作品来交叉锁定时, benchmark web question, external evidence lookup
summary: 题目给出短片时长、年份、剧情梗概，并通过导演学历和剪辑师另一部作品来交叉锁定时
confidence: 0.70
---
# 短片识别（多重剧组+学历线索）

## When to use
- Question type: 短片识别（多重剧组+学历线索）
- Trigger: 题目给出短片时长、年份、剧情梗概，并通过导演学历和剪辑师另一部作品来交叉锁定时

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：提取硬约束——2015年、18分钟、乡村学校新教师题材；以及人物约束——导演本科英文文学、剪辑师剪过2009年142分钟战争片
2. 第2步：先确定2009年的142分钟战争片（很可能是知名作品），通过其剪辑师名字反查其参与的2015年短片
3. 第3步：用剧情和时长在BFI/IMDb短片库中比对候选；再验证导演本科是否为英文文学
4. 第4步：注意片长精确为18分钟，避免选到题材相近但时长不符的短片；标题应给出官方英文标题

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
误把'乡村教师'当成长片或纪录片去搜；忽略剪辑师这条强约束直接靠剧情猜测
