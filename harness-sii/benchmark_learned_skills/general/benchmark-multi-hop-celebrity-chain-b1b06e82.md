---
skill_id: benchmark-multi-hop-celebrity-chain-b1b06e82
title: 多跳明星链条（歌手→专辑→歌曲→说唱歌手→演员）
domains: general, benchmark, web, evidence
triggers: 多跳明星链条（歌手→专辑→歌曲→说唱歌手→演员）, 通过歌手生平→专辑命名→同名歌曲→说唱歌手真名→同姓演员→某小说改编电影女主→毕业年份链式推理, benchmark web question, external evidence lookup, ent.chain.singer-to-actress-pageant
summary: 通过歌手生平→专辑命名→同名歌曲→说唱歌手真名→同姓演员→某小说改编电影女主→毕业年份链式推理
confidence: 0.70
---
# 多跳明星链条（歌手→专辑→歌曲→说唱歌手→演员）

## When to use
- Question type: 多跳明星链条（歌手→专辑→歌曲→说唱歌手→演员）
- Trigger: 通过歌手生平→专辑命名→同名歌曲→说唱歌手真名→同姓演员→某小说改编电影女主→毕业年份链式推理

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先锁定歌手——大学1970-1990成立，歌手1980年代毕业，获7项大奖18次提名（截至2023），有一张专辑标题来自父母口头禅
2. 第2步：找出该专辑的曲目表，与2020年代初某说唱歌手的同名歌曲交叉匹配，得到说唱歌手真实姓氏
3. 第3步：列出'倒数第三部小说由著名作家所著且被改编成电影'的候选；查电影中男主角love interest女演员的姓氏，匹配步骤2的姓
4. 第4步：验证该女演员的毕业年份等于电影上映年份，确保是同一人；输出完整全名（含middle name）

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
在长链条中只验证最后一跳，忽略中间约束；输出演员艺名而非全名（含中间名）