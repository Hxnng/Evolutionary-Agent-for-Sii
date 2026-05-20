---
skill_id: benchmark-nigerian-influencer-host-ambassador-0b20dbc7
title: 影响者身份多约束识别（节目+代言+家庭排序）
domains: general, benchmark, web, evidence
triggers: 影响者身份多约束识别（节目+代言+家庭排序）, 题目通过 YouTube vlog、谈话节目主持人（生于 1980 年代）、MIT+商学院出身公司创始人、家中老二等线索定位一位影响者。, benchmark web question, external evidence lookup
summary: 题目通过 YouTube vlog、谈话节目主持人（生于 1980 年代）、MIT+商学院出身公司创始人、家中老二等线索定位一位影响者。
confidence: 0.70
---
# 影响者身份多约束识别（节目+代言+家庭排序）

## When to use
- Question type: 影响者身份多约束识别（节目+代言+家庭排序）
- Trigger: 题目通过 YouTube vlog、谈话节目主持人（生于 1980 年代）、MIT+商学院出身公司创始人、家中老二等线索定位一位影响者。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先解析最有判别力的约束：2016 年成为某品牌大使，品牌创始人是 MIT 校友 + 商学院毕业（提示尼日利亚/非洲科技公司创始人）；以及 2022 年她在某 1980 年代出生主持人的节目中主持谈话环节。
2. 第2步：搜索 'MIT alumnus founder Nigeria company brand ambassador 2016 female influencer YouTube vlog'，结合 'talk segment host 2022 show host born 1980s'。
3. 第3步：核对候选人是否为四个孩子中的老二，YouTube vlog 系列启动时间是否晚于其职业开端若干年，且整体职业生涯超过 10 年。
4. 第4步：注意区分'主持谈话环节'与'整档节目主持'，主持人是另一位人物，不要把节目主持人当成答案。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
常见错误是把节目正主持人误填为答案。题目问的是负责'谈话 segment'的影响者，而非节目本身的 host。
