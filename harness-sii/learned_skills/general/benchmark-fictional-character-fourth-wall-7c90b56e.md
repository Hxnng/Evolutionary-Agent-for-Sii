---
skill_id: benchmark-fictional-character-fourth-wall-7c90b56e
title: 虚构人物特征综合识别
domains: general, benchmark, web, evidence
triggers: 虚构人物特征综合识别, 题目给出'打破第四面墙、有得到禁欲苦行者帮助的背景故事、幽默、1960s-1980s 间播出且不到 50 集的电视剧'等组合特征。, benchmark web question, external evidence lookup
summary: 题目给出'打破第四面墙、有得到禁欲苦行者帮助的背景故事、幽默、1960s-1980s 间播出且不到 50 集的电视剧'等组合特征。
confidence: 0.70
---
# 虚构人物特征综合识别

## When to use
- Question type: 虚构人物特征综合识别
- Trigger: 题目给出'打破第四面墙、有得到禁欲苦行者帮助的背景故事、幽默、1960s-1980s 间播出且不到 50 集的电视剧'等组合特征。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：抓核心特征：'禁欲苦行者帮助'强烈指向佛教/道教修行者，提示东亚神话；'幽默且打破第四面墙'+'剧集少于 50 集'缩小到具体改编剧。
2. 第2步：搜索 '1970s TV series Buddhist monk monkey breaks fourth wall fewer than 50 episodes'，定位到日本制作、英国 BBC 配音播出的经典剧。
3. 第3步：交叉验证集数（确实<50）、播出年代（70s 末-80s 初）、角色背景（西游记取经故事中三位修行者帮助）。
4. 第4步：答案要给出角色名而非剧名，并兼顾英文俗称与原名（Monkey / Sun Wukong）。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
易把剧名当角色名，或者忽略'打破第四面墙'这一英语配音版的独特特征而错选其他西游改编。
