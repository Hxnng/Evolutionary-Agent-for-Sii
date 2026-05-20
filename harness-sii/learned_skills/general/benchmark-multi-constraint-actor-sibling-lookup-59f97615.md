---
skill_id: benchmark-multi-constraint-actor-sibling-lookup-59f97615
title: 多约束名人身份识别+亲属信息检索
domains: general, benchmark, web, evidence
triggers: 多约束名人身份识别+亲属信息检索, 题目描述一位演员/艺人的多个职业里程碑（出道时间、突破作品、导演、获奖动画配音等），最终要求回答其亲属的某项信息, benchmark web question, external evidence lookup
summary: 题目描述一位演员/艺人的多个职业里程碑（出道时间、突破作品、导演、获奖动画配音等），最终要求回答其亲属的某项信息
confidence: 0.70
---
# 多约束名人身份识别+亲属信息检索

## When to use
- Question type: 多约束名人身份识别+亲属信息检索
- Trigger: 题目描述一位演员/艺人的多个职业里程碑（出道时间、突破作品、导演、获奖动画配音等），最终要求回答其亲属的某项信息

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先解析所有可定位线索，特别关注唯一性强的锚点——'70年代首次有偿表演'+'数年后在斯皮尔伯格电影中突破'，这强烈指向斯皮尔伯格早期标志性电影（如《E.T.》《Indiana Jones》《Goonies》《Hook》等）的儿童/青年演员
2. 第2步：基于'出道40年+'（截至2021即1981前出道）+'参与获奥斯卡奖的动画配音'，搜索斯皮尔伯格电影童星名单，并交叉过滤其后续是否参与过奥斯卡获奖动画（如《Toy Story》系列等）
3. 第3步：锁定候选人后，检索其家族信息，确认是否有'小7岁的弟弟/妹妹'，并提取该兄弟姐妹的名字；用多源（维基、IMDb、采访）核实年龄差精确为7岁
4. 第4步：只输出兄弟姐妹的first name，不要把演员本人的名字写出；确认是同父同母兄弟而非异父异母或继亲

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把斯皮尔伯格电影范围限制太窄；也容易把'7岁差距'近似为6或8岁的兄弟姐妹；要严格按年龄差筛选
