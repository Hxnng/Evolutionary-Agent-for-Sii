---
skill_id: benchmark-racing-driver-multi-clue-identify-12d1615e
title: 多线索赛车手身份识别
domains: general, benchmark, web, evidence
triggers: 多线索赛车手身份识别, 线索含赛车手的绰号、跨级别冠军、家族背景、欧洲公园广场命名、酒精轶事、语言能力、F1事故等组合线索, benchmark web question, external evidence lookup, sport.f1.driver.multi-bio
summary: 线索含赛车手的绰号、跨级别冠军、家族背景、欧洲公园广场命名、酒精轶事、语言能力、F1事故等组合线索
confidence: 0.70
---
# 多线索赛车手身份识别

## When to use
- Question type: 多线索赛车手身份识别
- Trigger: 线索含赛车手的绰号、跨级别冠军、家族背景、欧洲公园广场命名、酒精轶事、语言能力、F1事故等组合线索

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：聚合最具唯一性的线索——'欧洲公园里有以他命名的广场'+'曾在一次比赛中超越两位世界冠军夺冠'+'卷入导致另一位车手死亡的事故'，这些都是史料级硬约束
2. 第2步：搜索'square named after F1 driver in European park'、'F1 driver passed two world champions to win'、致死事故配对，初步圈定南美/欧洲老牌车手候选
3. 第3步：用'家庭机械背景'（父亲/兄弟与赛车机械相关）+'55-60岁仍在比赛'（说明跨界到CART/IndyCar或Stock Car）+'7冠王粉丝'（暗示舒马赫或汉密尔顿粉丝）做交叉验证
4. 第4步：注意年代——'最后一次起跑55-60岁'排除年轻一代；确认事故指代是Monza 1978 Peterson事件等历史性事件；输出全名而非昵称

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
不要被'绰号合适'误导去查Schumacher/Senna；要意识到这是描述一位既拿过F1冠军又跨界CART/Stock Car的资深巴西车手