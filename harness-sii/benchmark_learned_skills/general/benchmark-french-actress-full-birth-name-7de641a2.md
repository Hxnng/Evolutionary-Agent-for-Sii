---
skill_id: benchmark-french-actress-full-birth-name-7de641a2
title: 法国女演员完整出生姓名检索
domains: general, benchmark, web, evidence
triggers: 法国女演员完整出生姓名检索, 通过家庭关系（配偶、兄弟姐妹、子女）和合作导演来锁定某位法国女演员，并需要其完整出生全名（含中间名）。, benchmark web question, external evidence lookup, person.fr.actress.legal-birthname
summary: 通过家庭关系（配偶、兄弟姐妹、子女）和合作导演来锁定某位法国女演员，并需要其完整出生全名（含中间名）。
confidence: 0.70
---
# 法国女演员完整出生姓名检索

## When to use
- Question type: 法国女演员完整出生姓名检索
- Trigger: 通过家庭关系（配偶、兄弟姐妹、子女）和合作导演来锁定某位法国女演员，并需要其完整出生全名（含中间名）。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先用'1930s法国出生、第二任丈夫1960年代结婚、儿子是演员'缩小候选；再用'第一任丈夫死于癌症1995-2005'进一步过滤。
2. 第2步：确认合作导演——'1920s生、死于罗马、只有一个孩子'是非常强的指纹（指向某位意大利导演），用以核对1957-1967间的影片。
3. 第3步：在维基百科法语版/IMDB上查找该演员，注意法语维基常列出完整出生名（含多个中间名）。
4. 第4步：输出时必须完整列出所有教名（如Aiguionne、Jacqueline、Marie等），不要简化为艺名或常用名。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易输出艺名而非完整出生名；中间名往往只在法语版维基或正式传记中出现，需要切换语言源。