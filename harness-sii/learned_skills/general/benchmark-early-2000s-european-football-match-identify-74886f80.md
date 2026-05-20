---
skill_id: benchmark-early-2000s-european-football-match-identify-74886f80
title: 足球比赛+替补球员识别
domains: general, benchmark, web, evidence
triggers: 足球比赛+替补球员识别, 题目给出一场21世纪初的欧洲顶级联赛比赛：主队1870年代成立、主教练在20岁时作为青训球员遇见配偶、客队助教是1970年代前队长、两队赛季总胜场35场，要求客队第三替补, benchmark web question, external evidence lookup
summary: 题目给出一场21世纪初的欧洲顶级联赛比赛：主队1870年代成立、主教练在20岁时作为青训球员遇见配偶、客队助教是1970年代前队长、两队赛季总胜场35场，要求客队第三替补
confidence: 0.70
---
# 足球比赛+替补球员识别

## When to use
- Question type: 足球比赛+替补球员识别
- Trigger: 题目给出一场21世纪初的欧洲顶级联赛比赛：主队1870年代成立、主教练在20岁时作为青训球员遇见配偶、客队助教是1970年代前队长、两队赛季总胜场35场，要求客队第三替补

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先锁定主队——'1870年代成立'的欧洲一线俱乐部很有限（如Aston Villa 1874、Bolton 1874、Birmingham 1875、Sheffield系等）；结合'2001年主教练20岁时在俱乐部青训认识配偶'查具体管理者
2. 第2步：再定位客队——'助教是1970s前队长'+具体赛季两队胜场合计35；用英超历史数据库（如11v11、Wikipedia赛季页）筛选这一组合
3. 第3步：找到具体比赛日期与首发替补名单后，按客队替补使用顺序定位第三个被换上的球员（看比赛报告中substitution顺序，而不是替补名单第三人）
4. 第4步：输出full name（含教名/常用名）；务必确认是'第三次换人上场的球员'而非替补席名单序号第3位

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
最大陷阱是混淆'替补名单第三人'与'实际第三次替补上场的人'；必须查比赛纪要中的换人时间顺序
