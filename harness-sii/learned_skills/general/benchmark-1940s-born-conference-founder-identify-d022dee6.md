---
skill_id: benchmark-1940s-born-conference-founder-identify-d022dee6
title: 多重职业身份人物识别（顾问+作者+会议创办人）
domains: general, benchmark, web, evidence
triggers: 多重职业身份人物识别（顾问+作者+会议创办人）, 目标人物1940年代出生、出生国已改名、男校校友、CNBC纪录片中谈某洲能源、创办会议系列、政府顾问、出版作者、播客主持, benchmark web question, external evidence lookup
summary: 目标人物1940年代出生、出生国已改名、男校校友、CNBC纪录片中谈某洲能源、创办会议系列、政府顾问、出版作者、播客主持
confidence: 0.70
---
# 多重职业身份人物识别（顾问+作者+会议创办人）

## When to use
- Question type: 多重职业身份人物识别（顾问+作者+会议创办人）
- Trigger: 目标人物1940年代出生、出生国已改名、男校校友、CNBC纪录片中谈某洲能源、创办会议系列、政府顾问、出版作者、播客主持

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：识别强约束——'出生国家现在已改名'（如英属印度、缅甸→Myanmar、波斯→伊朗、罗德西亚→津巴布韦等）+ '创办一个conference portfolio'（系列商务峰会）+ 'CNBC纪录片谈某洲能源'
2. 第2步：搜索'founder conference Africa CNBC energy documentary'类组合查询，圈定非洲商务峰会创办人；结合'1970年代起担任政府顾问'缩小到资深商人
3. 第3步：核对其'1940年代生于现已改名的国家'（很可能是英属印度→印度独立前）+'百年以上历史男校'+'走过六大洲'，并验证其著作及播客
4. 第4步：输出包含尊称/学位（如适用）的姓名；不要把其公司CEO身份与会议创办身份混淆

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
'出生国改名'容易误判为苏联系国家；'六大洲访问'是装饰线索不要过度加权；关键还是会议系列+CNBC纪录片
