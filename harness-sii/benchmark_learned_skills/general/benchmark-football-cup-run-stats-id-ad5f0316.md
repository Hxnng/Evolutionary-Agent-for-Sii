---
skill_id: benchmark-football-cup-run-stats-id-ad5f0316
title: 球队赛季杯赛战绩反查+杯赛历史榜首
domains: general, benchmark, web, evidence
triggers: 球队赛季杯赛战绩反查+杯赛历史榜首, 线索含某欧洲球队的成立年代、欧冠/欧战夺冠年代，再给出一届国内杯赛从16强到决赛的详细统计（进球、犯规牌、平局数）, benchmark web question, external evidence lookup, sport.cup.stats.position-record
summary: 线索含某欧洲球队的成立年代、欧冠/欧战夺冠年代，再给出一届国内杯赛从16强到决赛的详细统计（进球、犯规牌、平局数）
confidence: 0.70
---
# 球队赛季杯赛战绩反查+杯赛历史榜首

## When to use
- Question type: 球队赛季杯赛战绩反查+杯赛历史榜首
- Trigger: 线索含某欧洲球队的成立年代、欧冠/欧战夺冠年代，再给出一届国内杯赛从16强到决赛的详细统计（进球、犯规牌、平局数）

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先用'20世纪初成立+1970年代第二次拿到主流欧洲联赛奖杯'锁定球队范围（注意是联赛冠军而非欧战）
2. 第2步：列出候选后，在该国国内杯赛（FA Cup/Coppa Italia等）中查找该球队某届从R16到决赛的逐场数据，匹配8球、15张牌、2场平局
3. 第3步：确定具体赛季后查询该届杯赛该队最终名次（冠军=1st）；再独立检索该国杯赛历史上夺冠次数最多的球队（截至2023）
4. 第4步：输出格式必须同时包含'名次'和'历史最多夺冠队'两个答案；不要混淆联赛冠军与杯赛冠军

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
把'major European League第二个奖杯'误读为欧冠/欧联；忽略'国内年度杯赛'与联赛是不同赛事