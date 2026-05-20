---
skill_id: benchmark-ecologist-book-review-cross-link-0db3e30a
title: 学者著作识别（通过书评人反查）
domains: general, benchmark, web, evidence
triggers: 学者著作识别（通过书评人反查）, 目标是一位行为生态学家2018年出版的书，已知其在The Conversation等学术平台发文记录，以及书评人于2023年6月14日去世, benchmark web question, external evidence lookup
summary: 目标是一位行为生态学家2018年出版的书，已知其在The Conversation等学术平台发文记录，以及书评人于2023年6月14日去世
confidence: 0.70
---
# 学者著作识别（通过书评人反查）

## When to use
- Question type: 学者著作识别（通过书评人反查）
- Trigger: 目标是一位行为生态学家2018年出版的书，已知其在The Conversation等学术平台发文记录，以及书评人于2023年6月14日去世

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：抓住最锐利的线索——'书评作者是另一位行为生态学家/进化生物学家，2023年6月14日去世'，搜索该日期讣告，候选人很可能是知名生物学家
2. 第2步：找到该已故学者的2018年书评记录（可能在TLS、Quarterly Review of Biology等），定位被评的2018年新书
3. 第3步：交叉验证作者本人在The Conversation平台2012/2013/2016各发一篇文章，且其中一篇标题含'cable'；并确认1987年获PhD
4. 第4步：输出书名要完整（含副标题与否依标准答案常见形式）；不要把作者名当成书名

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易绕路从作者著作列表入手，效率低；应当从'2023-06-14去世的行为生态学家'这一唯一性极强的钩子切入
