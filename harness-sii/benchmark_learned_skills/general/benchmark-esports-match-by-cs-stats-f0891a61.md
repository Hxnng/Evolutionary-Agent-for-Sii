---
skill_id: benchmark-esports-match-by-cs-stats-f0891a61
title: 电竞比赛识别（CS数+比赛时长+选手生日）
domains: general, benchmark, web, evidence
triggers: 电竞比赛识别（CS数+比赛时长+选手生日）, 线索含英雄联盟某场决赛G1的多名选手CS区间、比赛精确时长、某选手生日、年份区间, benchmark web question, external evidence lookup, esport.lol.cs-clock.final
summary: 线索含英雄联盟某场决赛G1的多名选手CS区间、比赛精确时长、某选手生日、年份区间
confidence: 0.70
---
# 电竞比赛识别（CS数+比赛时长+选手生日）

## When to use
- Question type: 电竞比赛识别（CS数+比赛时长+选手生日）
- Trigger: 线索含英雄联盟某场决赛G1的多名选手CS区间、比赛精确时长、某选手生日、年份区间

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先用'1998年11月出生的LoL职业选手'缩小范围（如Faker生于1996，需查同期明星选手）
2. 第2步：以该选手2016-2022年参加过的playoff决赛为候选，列出他所有Finals G1记录
3. 第3步：用Leaguepedia/Gol.gg查每场G1的四名选手CS数和比赛时长39:56，逐一对比四个CS区间
4. 第4步：答案需包含赛事完整名称+年份+赛段（如'YYYY [赛区] [Spring/Summer] Playoffs'）；注意是Playoffs而非Worlds或MSI

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
把生日线索套到错误选手；忽略'Playoffs'限定词输出成赛季决赛或国际赛