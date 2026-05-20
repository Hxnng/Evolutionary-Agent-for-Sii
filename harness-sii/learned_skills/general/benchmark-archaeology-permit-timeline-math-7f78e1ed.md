---
skill_id: benchmark-archaeology-permit-timeline-math-7f78e1ed
title: 考古/地产开发事件链与时间倒推
domains: general, benchmark, web, evidence
triggers: 考古/地产开发事件链与时间倒推, 题目给出地产开发停工进行考古、出口许可证年份与样本数量，要求查 13 年前监督试坑的考古公司。, benchmark web question, external evidence lookup
summary: 题目给出地产开发停工进行考古、出口许可证年份与样本数量，要求查 13 年前监督试坑的考古公司。
confidence: 0.70
---
# 考古/地产开发事件链与时间倒推

## When to use
- Question type: 考古/地产开发事件链与时间倒推
- Trigger: 题目给出地产开发停工进行考古、出口许可证年份与样本数量，要求查 13 年前监督试坑的考古公司。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：锁定关键稀有数字——25 套公寓+37 车位、175 个同位素/DNA 样本出口许可、9 个试坑，这些组合很可能指向某个具体南非考古案例（19 世纪小屋被拆）。
2. 第2步：搜索 'archaeological excavation 25 apartments 37 parking 19th century cottages export permit isotope DNA 175 samples'，定位到具体地块（很可能是开普敦地区某项目），并查找出口许可年份。
3. 第3步：从出口许可年份倒推 13 年，找该日期前后监督 9 个试坑的考古承包商名字；阅读 HIA/考古报告 PDF 中 'test pits monitored by' 字样。
4. 第4步：注意区分'监督试坑的公司'与'后期发掘的公司'，它们可能不同；以早期阶段的承包商为准。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
常见错误是把主发掘单位（更出名）当成 13 年前的试坑监督方。务必按时间线分别匹配早期勘探与后期发掘的不同机构。
