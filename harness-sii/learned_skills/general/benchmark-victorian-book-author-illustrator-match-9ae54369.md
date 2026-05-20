---
skill_id: benchmark-victorian-book-author-illustrator-match-9ae54369
title: 书籍标题识别（作者+插画师双向约束）
domains: general, benchmark, web, evidence
triggers: 书籍标题识别（作者+插画师双向约束）, 需要根据作者生平与插画师生平的双重线索来锁定一本特定年份出版书籍的标题。, benchmark web question, external evidence lookup
summary: 需要根据作者生平与插画师生平的双重线索来锁定一本特定年份出版书籍的标题。
confidence: 0.70
---
# 书籍标题识别（作者+插画师双向约束）

## When to use
- Question type: 书籍标题识别（作者+插画师双向约束）
- Trigger: 需要根据作者生平与插画师生平的双重线索来锁定一本特定年份出版书籍的标题。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先锁定作者——'1860s出生、父亲是拍卖师、1888-1901年间用本名出版23本书'，这是高度具体的指纹，搜索维多利亚时代多产作家列表。
2. 第2步：列出该作者1898年出版的所有作品候选，并对每本查询其插画师。
3. 第3步：核验插画师约束——'1900年失去手足、曾在皇家学院（Royal Academy）展出'，定位到名艺术家家族（如Rackham兄弟），交叉确认其插图作品。
4. 第4步：注意1898年的版本可能是再版/新插图版，原作者与作品标题需精确匹配（区分Richard Harris Barham原作与重新插图版本的归属）。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
不要忽视'illustrated by'可能指向再版书的新插画师；作者的23本书可能含合集和散文集，需精准定位1898年那本。
