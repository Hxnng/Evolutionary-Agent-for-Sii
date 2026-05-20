---
skill_id: benchmark-multi-constraint-biography-venezuelan-cinema-d7964047
title: 多约束人物身份识别（导演/电影从业者）
domains: general, benchmark, web, evidence
triggers: 多约束人物身份识别（导演/电影从业者）, 当问题给出多个传记式约束（出生年代、教育背景、师承关系、职业经历）来锁定某位电影行业人物时调用。, benchmark web question, external evidence lookup, film.venezuela.director.budget
summary: 当问题给出多个传记式约束（出生年代、教育背景、师承关系、职业经历）来锁定某位电影行业人物时调用。
confidence: 0.70
---
# 多约束人物身份识别（导演/电影从业者）

## When to use
- Question type: 多约束人物身份识别（导演/电影从业者）
- Trigger: 当问题给出多个传记式约束（出生年代、教育背景、师承关系、职业经历）来锁定某位电影行业人物时调用。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先将问题拆解为可验证的原子事实清单：出生年代、求学地点（城市+学校）、师承导演（两位，分别附出生月份和年代）、职业活动年代（1990s）和行业背景（资金有限的电影业）。
2. 第2步：对地理谜题先解码——'委内瑞拉主要城市，建立于7月，1567年之后、1563年（含）之前'实际是逻辑陷阱（应理解为 founded in July, after 1557 但 before 1563 等修正读法），优先匹配Caracas（1567年7月）；同时检索120 Madison Ave NYC的戏剧学校（American Academy of Dramatic Arts）。
3. 第3步：对两位导演分别用生日窗口在维基百科/IMDB检索（4月生1930-1942、12月生1920-1932），再交叉查询'assistant director 4 years'与候选委内瑞拉导演的合作记录。
4. 第4步：最终用1990s委内瑞拉电影业的发行垄断和上映困境（公认的Venezuelan cinema crisis）来确认人物身份；输出全名前确认该人物所有约束均满足，不要被同名人物干扰。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易被地理时间约束的措辞陷阱误导（'after X but before Y'看似矛盾），以及忽略'helper/assistant'与'collaborator'的区别。