---
skill_id: benchmark-early-20c-scientist-car-accident-identify-720f71e9
title: 20世纪早期科学家生平多约束识别
domains: general, benchmark, web, evidence
triggers: 20世纪早期科学家生平多约束识别, 目标人物有精确出生月份区间、死亡月份区间、车祸去世、16岁出书、母亲早逝于癌症、就读/任职于某世纪初创立的大学, benchmark web question, external evidence lookup, sci.early20c.car-accident.egypt
summary: 目标人物有精确出生月份区间、死亡月份区间、车祸去世、16岁出书、母亲早逝于癌症、就读/任职于某世纪初创立的大学
confidence: 0.70
---
# 20世纪早期科学家生平多约束识别

## When to use
- Question type: 20世纪早期科学家生平多约束识别
- Trigger: 目标人物有精确出生月份区间、死亡月份区间、车祸去世、16岁出书、母亲早逝于癌症、就读/任职于某世纪初创立的大学

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：聚焦最强约束——'1950-1953年8月车祸去世'+'16岁出书'+'一等荣誉理学士1937-1940'，这强烈指向某位早逝的女性核科学家或类似学者
2. 第2步：搜索'scientist died car accident August 1952'类查询；结合'1906-1909年12月成立的大学'（开罗大学成立于1908年12月）锁定埃及/中东地区学者
3. 第3步：交叉验证母亲死于癌症、父亲投资小旅馆、16岁著书等传记细节；确认大学创立日期符合窗口
4. 第4步：注意名字的英文转写多种形式，选择最常见的Wiki拼写；不要混淆同期其他早逝科学家

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
不要被'一等荣誉学位'误导只看英国体系；中东大学也使用英式荣誉体系；车祸细节要与传记吻合（出租车在赴会途中）