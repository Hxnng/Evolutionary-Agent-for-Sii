---
skill_id: benchmark-1980s-anime-allegory-article-author-22998b37
title: 通过文章作者奖项识别被分析的电影
domains: general, benchmark, web, evidence
triggers: 通过文章作者奖项识别被分析的电影, 已知2023年某篇文章分析1980s动画电影的寓言主题，且作者获过特定建筑/艺术奖（AIA Henry Adams Medal）。, benchmark web question, external evidence lookup
summary: 已知2023年某篇文章分析1980s动画电影的寓言主题，且作者获过特定建筑/艺术奖（AIA Henry Adams Medal）。
confidence: 0.70
---
# 通过文章作者奖项识别被分析的电影

## When to use
- Question type: 通过文章作者奖项识别被分析的电影
- Trigger: 已知2023年某篇文章分析1980s动画电影的寓言主题，且作者获过特定建筑/艺术奖（AIA Henry Adams Medal）。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：AIA Henry Adams Medal是颁给优秀建筑学生的奖项，搜索获奖者并筛选写过电影评论的人。
2. 第2步：交叉检索该作者2023年发表的有关动画电影的文章。
3. 第3步：核对文章中讨论的1980s动画电影（如Akira、Nausicaä、Laputa等），匹配寓言主题分析角度。
4. 第4步：输出电影标题时使用国际通用名，并确认发行年代确实为1980s。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
AIA Henry Adams Medal颁奖人数众多，需结合写作领域筛选；不要把动画导演的访谈与影评作者混淆。
