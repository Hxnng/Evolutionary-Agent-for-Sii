---
skill_id: benchmark-game-art-director-via-mission-fingerprint-09b4efd1
title: 游戏美术总监识别
domains: general, benchmark, web, evidence
triggers: 游戏美术总监识别, 题目以游戏第六关以某欧洲国家命名、含限时主目标+摧毁特定敌军次目标作为'关卡指纹'，并叠加2010后PC发行、两人创立的非美国工作室等约束，问图形团队的美术总监姓名, benchmark web question, external evidence lookup
summary: 题目以游戏第六关以某欧洲国家命名、含限时主目标+摧毁特定敌军次目标作为'关卡指纹'，并叠加2010后PC发行、两人创立的非美国工作室等约束，问图形团队的美术总监姓名
confidence: 0.70
---
# 游戏美术总监识别

## When to use
- Question type: 游戏美术总监识别
- Trigger: 题目以游戏第六关以某欧洲国家命名、含限时主目标+摧毁特定敌军次目标作为'关卡指纹'，并叠加2010后PC发行、两人创立的非美国工作室等约束，问图形团队的美术总监姓名

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：把'第六关以欧洲国家命名+限时主目标+摧毁敌方单位次目标'当作关卡指纹，强烈指向战术/策略类游戏(如Wargame, Steel Division, R.U.S.E等Eugen Systems作品)
2. 第2步：搜索 '[候选游戏] mission 6 [国家名] objectives'，确认关卡设计；同时查工作室创始人数量(2人)、所在国(法国等非美国)
3. 第3步：在游戏的演职员表(credits)、工作室官网、MobyGames、LinkedIn中查找'Art Director'/'Graphics Art Director'条目，并交叉比对
4. 第4步：题目要求'图形团队的美术总监'(graphical team's art director)，与一般art director可能不同；必须按credits栏目精确匹配头衔

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把工作室创意总监、首席美术或其他相关岗位的人名当成答案；正确做法是严格按credits中graphical/graphics team的art director条目
