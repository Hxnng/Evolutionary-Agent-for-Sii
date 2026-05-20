---
skill_id: benchmark-tv-series-production-company-via-actor-3f0a7f34
title: 通过演员生平定位电视剧制作公司
domains: general, benchmark, web, evidence
triggers: 通过演员生平定位电视剧制作公司, 已知演员童年成名经历、所演剧集（家庭剧+真实人物剧+医疗剧）、就读国际学校特征、结婚年份，求某剧的制作公司。, benchmark web question, external evidence lookup
summary: 已知演员童年成名经历、所演剧集（家庭剧+真实人物剧+医疗剧）、就读国际学校特征、结婚年份，求某剧的制作公司。
confidence: 0.70
---
# 通过演员生平定位电视剧制作公司

## When to use
- Question type: 通过演员生平定位电视剧制作公司
- Trigger: 已知演员童年成名经历、所演剧集（家庭剧+真实人物剧+医疗剧）、就读国际学校特征、结婚年份，求某剧的制作公司。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：解析时间锚——YouTube成立(2005)到首代iPad发布(2010)之间，即家庭剧停播于2005-2010。
2. 第2步：用'2001年成立的国际学校、2020年有两个校区（幼儿园与高中）'定位演员所在国家/地区（可能是非洲法语区或加勒比）。
3. 第3步：用'2021年结婚（拜登就职年）'缩小候选；结合演员国籍找到家庭剧名称及其制片公司。
4. 第4步：制作公司名称需精确（区分发行方与制作方），核对剧集片头/IMDB的Production company字段。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
易把发行公司或电视台当作制作公司；非英语地区剧集需用本地语言资料源（如海地/法语非洲）。
