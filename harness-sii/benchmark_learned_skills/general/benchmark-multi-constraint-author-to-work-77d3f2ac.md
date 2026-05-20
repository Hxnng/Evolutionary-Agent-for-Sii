---
skill_id: benchmark-multi-constraint-author-to-work-77d3f2ac
title: 作者生平线索反推作品
domains: general, benchmark, web, evidence
triggers: 作者生平线索反推作品, 通过作者的多条传记线索（学历、职业、语言、观点、旅行等）+ 作品属性（首版语言、出版日期、主题、被禁国家）来锁定一本书时, benchmark web question, external evidence lookup, lit.banned-country.novel.title-en
summary: 通过作者的多条传记线索（学历、职业、语言、观点、旅行等）+ 作品属性（首版语言、出版日期、主题、被禁国家）来锁定一本书时
confidence: 0.70
---
# 作者生平线索反推作品

## When to use
- Question type: 作者生平线索反推作品
- Trigger: 通过作者的多条传记线索（学历、职业、语言、观点、旅行等）+ 作品属性（首版语言、出版日期、主题、被禁国家）来锁定一本书时

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：拆解为两类约束——作品类（法语首版、2023前出版、对某国的文化分析、在该国被禁）和作者类（两次高考失败1975-1985、与父母同行业工作5年、关于痛苦与写作的观点、1998左右首次到访纽约）
2. 第2步：先用作品约束做候选检索，搜索'novel banned in [country] cultural analysis French original'，并结合'被禁'这一强信号联想到阿尔及利亚/中国/伊朗等可能国家；交叉检索法语原版小说与英文译名
3. 第3步：用作者传记线索（高考两次失败、父母教师身份、痛苦与写作哲学、1998年纽约首访）在Wikipedia/采访资料中比对，确认作者身份后回溯其代表作
4. 第4步：必须输出该书的英文译名而非法文原名；确认该书确实是'对某国的文化分析'且在该国被禁，避免混淆作者的其他作品

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把作者最有名的作品当作答案，但需的是符合'文化分析+被禁+法语首版'三重约束的特定作品；也容易输出法语原名而非英文译名