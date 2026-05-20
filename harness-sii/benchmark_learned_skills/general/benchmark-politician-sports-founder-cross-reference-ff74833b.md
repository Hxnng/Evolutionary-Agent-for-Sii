---
skill_id: benchmark-politician-sports-founder-cross-reference-ff74833b
title: 政治家+体育队创始人+校友交叉检索
domains: general, benchmark, web, evidence
triggers: 政治家+体育队创始人+校友交叉检索, 目标人物同时具备政治身份（州议员）、体育队创始人身份，并且大学校友里有特定真人秀冠军, benchmark web question, external evidence lookup, person.politician.team-founder.alumni
summary: 目标人物同时具备政治身份（州议员）、体育队创始人身份，并且大学校友里有特定真人秀冠军
confidence: 0.70
---
# 政治家+体育队创始人+校友交叉检索

## When to use
- Question type: 政治家+体育队创始人+校友交叉检索
- Trigger: 目标人物同时具备政治身份（州议员）、体育队创始人身份，并且大学校友里有特定真人秀冠军

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先解析最稀有的钩子——'与某位早期TUF(The Ultimate Fighter)冠军是校友'，TUF始于2005年，列出早期赛季冠军并查其大学
2. 第2步：以该大学为锚点反向搜索'校友 founded sports team 1930-1970'+'state House of Representatives 1935-1955'，缩小到美国某州的政商人物
3. 第3步：用出生年份（20世纪早期，约1900-1925）和州议员任期窗口交叉验证；确认其创立的职业体育队名称与年份
4. 第4步：注意'state House of Representatives'指州议会而非联邦众议院；输出full name，确认是否还做过州长等更高职位（防止重名）

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易忽视TUF这一冷门线索；也容易把'professional sports team'误判为业余联盟；务必锁定真正的'职业'体育联盟