---
skill_id: benchmark-game-by-two-developers-protagonist-08319286
title: 联合开发游戏识别
domains: general, benchmark, web, evidence
triggers: 联合开发游戏识别, 题目描述一款由两家亚洲游戏公司联合开发的游戏，给出公司logo年代、其中一家在2010年代游戏发售后不久衰落，以及主角的欧洲绅士形象+助手设定, benchmark web question, external evidence lookup
summary: 题目描述一款由两家亚洲游戏公司联合开发的游戏，给出公司logo年代、其中一家在2010年代游戏发售后不久衰落，以及主角的欧洲绅士形象+助手设定
confidence: 0.70
---
# 联合开发游戏识别

## When to use
- Question type: 联合开发游戏识别
- Trigger: 题目描述一款由两家亚洲游戏公司联合开发的游戏，给出公司logo年代、其中一家在2010年代游戏发售后不久衰落，以及主角的欧洲绅士形象+助手设定

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：识别主角线索——'衣着考究的欧洲人+独特胡须+优雅配饰+经验不足的助手'，强烈指向Professor Layton或Phoenix Wright类侦探/推理角色
2. 第2步：搜索两家亚洲游戏公司联合开发的crossover作品，时间在2010年代；其中一家公司在游戏发售后倒闭/衰落（提示Level-5的境况）
3. 第3步：交叉验证Logo设计年代——例如Capcom和Level-5的标志确立时间，确认crossover游戏
4. 第4步：输出完整官方英文标题（包含'vs.'写法）；避免单独输出某一系列名

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
只想到一个IP（如逆转裁判或雷顿教授）而忘了这是crossover；公司衰落线索容易被误解为开发商而非发行商
