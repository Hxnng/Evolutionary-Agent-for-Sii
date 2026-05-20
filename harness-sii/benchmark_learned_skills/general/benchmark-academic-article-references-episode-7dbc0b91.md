---
skill_id: benchmark-academic-article-references-episode-7dbc0b91
title: 学术文章交叉引用动画剧集
domains: general, benchmark, web, evidence
triggers: 学术文章交叉引用动画剧集, 通过2021年合著文章+作者职务（2021年任某1927年成立学院的Dean of Student Affairs）+ 文章讨论的2011年首播动画+ 文章引用了2020年另..., benchmark web question, external evidence lookup, acad.ref-chain.episode-title.2021
summary: 通过2021年合著文章+作者职务（2021年任某1927年成立学院的Dean of Student Affairs）+ 文章讨论的2011年首播动画+ 文章引用了2020年另一篇文章讨论的某集
confidence: 0.70
---
# 学术文章交叉引用动画剧集

## When to use
- Question type: 学术文章交叉引用动画剧集
- Trigger: 通过2021年合著文章+作者职务（2021年任某1927年成立学院的Dean of Student Affairs）+ 文章讨论的2011年首播动画+ 文章引用了2020年另一篇文章讨论的某集

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先锁定2011年首播的动画TV系列（候选包括《Adventure Time》《Bob's Burgers》《Pound Puppies》等），缩小到学术研究关注度较高者
2. 第2步：在Google Scholar/JSTOR中搜索该动画+2021年的合著文章，验证作者之一在1927年成立的学院担任Dean of Student Affairs
3. 第3步：定位该2021文章的参考文献，找到其引用的2020年学术文章，再确认该2020文章具体讨论的剧集名
4. 第4步：输出剧集的官方英文标题，注意拼写（特别是创造性合成词如'Tweentrepreneurs'）

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
把2021文章讨论的剧集与2020文章讨论的剧集混为一谈；忽略要回答的是被引用的那一集而非文章的主话题集