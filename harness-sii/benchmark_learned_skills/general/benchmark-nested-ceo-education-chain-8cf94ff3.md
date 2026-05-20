---
skill_id: benchmark-nested-ceo-education-chain-8cf94ff3
title: 多层嵌套约束的人物身份识别
domains: general, benchmark, web, evidence
triggers: 多层嵌套约束的人物身份识别, 通过 A 公司 CEO → 投资 B 公司 → B 公司 CEO 的教育背景（且大学有改名史）等多层链条描述目标人物。, benchmark web question, external evidence lookup, corp.ceo.chain.edu-rename
summary: 通过 A 公司 CEO → 投资 B 公司 → B 公司 CEO 的教育背景（且大学有改名史）等多层链条描述目标人物。
confidence: 0.70
---
# 多层嵌套约束的人物身份识别

## When to use
- Question type: 多层嵌套约束的人物身份识别
- Trigger: 通过 A 公司 CEO → 投资 B 公司 → B 公司 CEO 的教育背景（且大学有改名史）等多层链条描述目标人物。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：从最具体的内层线索入手——B 公司 CEO 的本科大学（1900-1930 创立、1920-1940 改为现名）和硕士大学（源自 1720-1780 创立的私立学院），列出候选大学（如改名史明确的常见大学）。
2. 第2步：用 LinkedIn、Crunchbase 和新闻检索同时满足这两所大学（本科+硕士）的科技/创业 CEO；再向外推导：哪家公司（A）在 2021 年前投资了 B 公司，并找出 A 公司 CEO。
3. 第3步：核验 A 公司 CEO 的大学是否创立于 1940-1990 区间、其婚姻状况是否公开，确认全部约束都被满足。
4. 第4步：注意区分'投资'与'收购'，以及 CEO 任期是否覆盖时间窗口（截至 2021/2023）。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易跳过内层 B 公司 CEO 直接猜 A 公司 CEO。必须按链条从最稀有约束反向定位，不要被'投资关系'误导成股权关系。