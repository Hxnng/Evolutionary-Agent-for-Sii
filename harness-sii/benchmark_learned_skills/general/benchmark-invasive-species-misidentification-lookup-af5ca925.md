---
skill_id: benchmark-invasive-species-misidentification-lookup-af5ca925
title: 入侵物种错认学名查询
domains: general, benchmark, web, evidence
triggers: 入侵物种错认学名查询, 线索含入侵昆虫的引入年(1916)、扩散历史、最初被错误鉴定，要求给出最初被误认为的物种学名, benchmark web question, external evidence lookup, bio.beetle.misid.1916
summary: 线索含入侵昆虫的引入年(1916)、扩散历史、最初被错误鉴定，要求给出最初被误认为的物种学名
confidence: 0.70
---
# 入侵物种错认学名查询

## When to use
- Question type: 入侵物种错认学名查询
- Trigger: 线索含入侵昆虫的引入年(1916)、扩散历史、最初被错误鉴定，要求给出最初被误认为的物种学名

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：用时间锚定甲虫：1916年首次发现的入侵甲虫 + 1960年代末扩散至全国 + 2017年6月2日发表的摘要；推断目标国可能是日本/新西兰等岛国
2. 第2步：搜索 'invasive beetle 1916 first record' + 'misidentified' + 'abstract 2017'，并直接查询2017年6月2日前后发表的相关学术摘要
3. 第3步：找到该甲虫的实际学名后，在原文献中查找 'previously misidentified as' / 'formerly known as' / 'initially identified as' 之类表述，获取被误认物种的属种名
4. 第4步：答案需要给完整二名法（属+种），注意拼写大小写，并核对该误认物种是否在形态相似的近缘类群内

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把该甲虫的正确学名当作答案输出；正确答案是'曾被错认成的'物种学名，需要在文献中精准定位'misidentified as'语句