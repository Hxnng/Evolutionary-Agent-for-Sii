---
skill_id: benchmark-dating-app-thesis-podcast-f52f43cf
title: 学术论文致谢内容深度检索
domains: general, benchmark, web, evidence
triggers: 学术论文致谢内容深度检索, 题目要求从 2020-2023 年某 1980-1990 年间成立的大学博士论文（主题为约会软件）的致谢中，找到作者提到的播客名。, benchmark web question, external evidence lookup
summary: 题目要求从 2020-2023 年某 1980-1990 年间成立的大学博士论文（主题为约会软件）的致谢中，找到作者提到的播客名。
confidence: 0.70
---
# 学术论文致谢内容深度检索

## When to use
- Question type: 学术论文致谢内容深度检索
- Trigger: 题目要求从 2020-2023 年某 1980-1990 年间成立的大学博士论文（主题为约会软件）的致谢中，找到作者提到的播客名。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先用 'PhD thesis dating apps 2020 2021 2022 2023 acknowledgments podcast breakup' 在 ProQuest、Google Scholar、各大学 institutional repository 中检索。
2. 第2步：用大学成立年份窗口（1980-1990）过滤候选大学（如某些较年轻的澳洲/英国大学），再用论文主题（dating apps）进一步缩小。
3. 第3步：打开论文 PDF 的 Acknowledgments 部分，确认作者提到分手 + 与电影节认识的人合开播客；再用作者姓名 + 'podcast' 搜索播客名称作交叉验证。
4. 第4步：确保播客名与作者匹配，而不是论文里只是引用的别人播客。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
常见错误是只搜论文标题而忽略致谢全文，或把作者引用的其他播客误当成她本人的播客。
