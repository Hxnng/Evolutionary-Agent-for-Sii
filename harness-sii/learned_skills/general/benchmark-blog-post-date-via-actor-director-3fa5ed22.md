---
skill_id: benchmark-blog-post-date-via-actor-director-3fa5ed22
title: 通过电影演员/导演反查博主身份并定位博文
domains: general, benchmark, web, evidence
triggers: 通过电影演员/导演反查博主身份并定位博文, 题目用出生月年+演员经历+电影导演出生年+博文内容片段共同锁定一篇博文的发布日期。, benchmark web question, external evidence lookup
summary: 题目用出生月年+演员经历+电影导演出生年+博文内容片段共同锁定一篇博文的发布日期。
confidence: 0.70
---
# 通过电影演员/导演反查博主身份并定位博文

## When to use
- Question type: 通过电影演员/导演反查博主身份并定位博文
- Trigger: 题目用出生月年+演员经历+电影导演出生年+博文内容片段共同锁定一篇博文的发布日期。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先抓硬约束——出现在 1994-1996 美国上映电影中、导演生于 1958-1960、自己生于 1980-1985 的 9-12 月；这能把候选缩到极少的童星。
2. 第2步：用 'child actor born 1980-1985 movie 1994-1996 director born 1959 blog' 组合搜索 IMDb 与个人博客；找到博主官网后用 site: 限定搜索博文。
3. 第3步：在博主博客中筛选 2014-2016 的 5-8 月发布日期，并核对正文是否含'父母在家某区域听音乐还在做某事''找到一个盒子''父母不愿谈论某事'三个细节，全部命中才确认。
4. 第4步：注意博文可能有重发日期或转载，最终要采用原始发布日，并以 月-日-年 格式输出。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
易错点是只看其中一个细节就锁定博文，或把博主其他相邻博文搞混。必须三段细节全部交叉命中，且日期落在月-年双重窗口内。
