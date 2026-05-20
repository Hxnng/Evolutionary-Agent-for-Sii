---
skill_id: benchmark-insufficient-evidence-acknowledgment-0be93343
title: 无法确定型问题（证据不足）
domains: general, benchmark, web, evidence
triggers: 无法确定型问题（证据不足）, 描述含一家美妆公司+创始人多重生平细节（贵族家庭工作、之前另一品牌3类初始产品、任命艺术爱好家族成员为总监），但线索具备多解可能, benchmark web question, external evidence lookup, biz.beauty.founder.underdetermined
summary: 描述含一家美妆公司+创始人多重生平细节（贵族家庭工作、之前另一品牌3类初始产品、任命艺术爱好家族成员为总监），但线索具备多解可能
confidence: 0.70
---
# 无法确定型问题（证据不足）

## When to use
- Question type: 无法确定型问题（证据不足）
- Trigger: 描述含一家美妆公司+创始人多重生平细节（贵族家庭工作、之前另一品牌3类初始产品、任命艺术爱好家族成员为总监），但线索具备多解可能

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：穷举满足'2000年代成立+创始人曾私下为贵族家庭工作'的美妆品牌候选
2. 第2步：对每个候选验证：是否之前有过另一品牌、首发是否仅3类产品、是否有家族成员被任命为总监
3. 第3步：若没有任何一个候选能同时满足全部约束，或多个候选都部分匹配但都无法完全确认，记录证据冲突
4. 第4步：当证据不足以唯一确定时，必须明确回答'无法确定'，不要为了完成任务而强行编造一个看似合理的名字

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
强行套用最有名的美妆创始人（如Tom Ford、Christian Louboutin、François Nars等）而忽略线索矛盾；过度自信