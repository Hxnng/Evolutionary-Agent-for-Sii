---
skill_id: benchmark-soccer-match-95min-freekick-0565890c
title: 特定足球比赛事件中的球员识别
domains: general, benchmark, web, evidence
triggers: 特定足球比赛事件中的球员识别, 用谜语化的方式描述两支球队及比赛进程（如95分钟任意球）来追溯具体球员。, benchmark web question, external evidence lookup
summary: 用谜语化的方式描述两支球队及比赛进程（如95分钟任意球）来追溯具体球员。
confidence: 0.70
---
# 特定足球比赛事件中的球员识别

## When to use
- Question type: 特定足球比赛事件中的球员识别
- Trigger: 用谜语化的方式描述两支球队及比赛进程（如95分钟任意球）来追溯具体球员。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：解码两支球队——'born out of discord among two parties'（因分裂而成立）与'identity evolved through several iterations'（多次改名）。
2. 第2步：结合'early 21st century'比分模式（一队全部早期进球，另一队后期进球）搜索匹配的真实比赛。
3. 第3步：定位比赛后查询第95分钟任意球执行者（通常是高大中锋或定位球专家）。
4. 第4步：确认球员是当时在场名单中的实际主罚者，而非仅靠球场录像猜测。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
球队谜面易误读，分裂成立的球队在葡萄牙/西班牙/南美都常见，需结合比赛年份和比分双重锚定。
