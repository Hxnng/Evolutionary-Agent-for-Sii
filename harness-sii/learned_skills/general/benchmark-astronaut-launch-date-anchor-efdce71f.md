---
skill_id: benchmark-astronaut-launch-date-anchor-efdce71f
title: 多重时间锚点反查人物配偶
domains: general, benchmark, web, evidence
triggers: 多重时间锚点反查人物配偶, 题目用'非洲音乐人 2000 年代就读大学（商学院距某车站<6km）+ 一篇采访文章发布在某次美欧联合载人发射两周年前 15-20 天'等线索定位欧洲出生宇航员的妻子名。, benchmark web question, external evidence lookup
summary: 题目用'非洲音乐人 2000 年代就读大学（商学院距某车站<6km）+ 一篇采访文章发布在某次美欧联合载人发射两周年前 15-20 天'等线索定位欧洲出生宇航员的妻子名。
confidence: 0.70
---
# 多重时间锚点反查人物配偶

## When to use
- Question type: 多重时间锚点反查人物配偶
- Trigger: 题目用'非洲音乐人 2000 年代就读大学（商学院距某车站<6km）+ 一篇采访文章发布在某次美欧联合载人发射两周年前 15-20 天'等线索定位欧洲出生宇航员的妻子名。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先识别'美国宇航员 + 欧洲出生宇航员同次发射'的候选——较新的联合发射任务（如 Crew-3 等 SpaceX 任务，欧洲宇航员搭乘）；锁定具体发射日期。
2. 第2步：用发射日期 + 2 年 - (15~20 天) 计算采访发布日窗口，搜索该窗口内非洲音乐人采访中'第一次录音时没完全清醒'的报道，反向确认非洲音乐人身份（间接验证）。
3. 第3步：确认欧洲宇航员身份（如来自德国、意大利、法国 ESA 成员），再查其公开资料中的妻子名字（仅 first name）。
4. 第4步：注意题目只要 first name，不带姓；并以 2023 年为信息截止点。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
陷阱是把'欧洲宇航员'理解错（如把俄罗斯宇航员当欧洲），或漏算两周年减 15-20 天的时间窗口导致采访锚定错位。
