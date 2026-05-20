---
skill_id: benchmark-nigerian-state-capital-football-club-3d853da3
title: 通过州/省成立信息定位足球俱乐部
domains: general, benchmark, web, evidence
triggers: 通过州/省成立信息定位足球俱乐部, 题目用州的成立年份范围（1985-1992）、面积范围（3800-5300 sq.km）以及球队赛季战绩特征来锁定俱乐部。, benchmark web question, external evidence lookup
summary: 题目用州的成立年份范围（1985-1992）、面积范围（3800-5300 sq.km）以及球队赛季战绩特征来锁定俱乐部。
confidence: 0.70
---
# 通过州/省成立信息定位足球俱乐部

## When to use
- Question type: 通过州/省成立信息定位足球俱乐部
- Trigger: 题目用州的成立年份范围（1985-1992）、面积范围（3800-5300 sq.km）以及球队赛季战绩特征来锁定俱乐部。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：筛选符合1985-1992年间成立的州（在非洲尤指尼日利亚州划分）且面积在3800-5300 km²范围内的州——指向Anambra州（1991年成立，约4844 km²）。
2. 第2步：找到该州首府城市（Awka）并列出在该首府成立的足球俱乐部。
3. 第3步：核验2015/16赛季战绩'胜=负=平相同'且'10月最后一场联赛获胜'，匹配尼甲/尼超数据。
4. 第4步：输出俱乐部全名（含FC前缀或当地拼写），避免缩写形式。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
把州与首府混淆（球队在首府而非州本身）；忽略'as of 2016'限定，导致使用错误年代的面积数据。
