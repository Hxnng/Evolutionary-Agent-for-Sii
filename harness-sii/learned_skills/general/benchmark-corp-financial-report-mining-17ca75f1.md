---
skill_id: benchmark-corp-financial-report-mining-17ca75f1
title: 企业年报具体数字检索
domains: general, benchmark, web, evidence
triggers: 企业年报具体数字检索, 题目提供多条公司特征线索（行业、CEO 言论、董事会决议时间线），要求从特定年度年报中查找精确数据。, benchmark web question, external evidence lookup
summary: 题目提供多条公司特征线索（行业、CEO 言论、董事会决议时间线），要求从特定年度年报中查找精确数据。
confidence: 0.70
---
# 企业年报具体数字检索

## When to use
- Question type: 企业年报具体数字检索
- Trigger: 题目提供多条公司特征线索（行业、CEO 言论、董事会决议时间线），要求从特定年度年报中查找精确数据。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先解析关键定位线索——行业（powerboats 制造商）、CEO 描述（无负债、订单积压、产能翻倍）、董事会回购计划的具体年份（2001、2005、2008），从而锁定公司身份。
2. 第2步：用 'powerboat manufacturer stock repurchase program 2001 2005 2008' 等组合词搜索，结合 SEC EDGAR 检索该公司 10-K/年报；目标年是 2022 财年的年报（通常在 2023 年初提交）。
3. 第3步：在 10-K 的 'Issuer Purchases of Equity Securities' 或 Treasury Stock 附注中定位 'shares remaining available for repurchase as of December 31, 2022'，与回购计划累计授权额做加减验证。
4. 第4步：注意题目限定的截止日期（2022-12-31），不要错用 2021 或 2023 年报数据；同时区分 'shares repurchased' 与 'shares remaining available'。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把累计已回购股数当成剩余可回购股数，或者混淆不同财年披露的余额。必须以年报披露的官方数字为准，不要用季度报告或新闻稿估算。
